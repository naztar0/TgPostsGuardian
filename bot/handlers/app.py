import logging
import json
from io import BytesIO
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from asyncio import sleep, gather

from django.db.models import Q
from channels.db import database_sync_to_async

from telethon import TelegramClient, types, events
from telethon.types import ChannelParticipantsAdmins, InputPeerChannel, InputChannel, MessageMediaPhoto
from telethon.tl.custom import Message
from telethon.tl.types import DialogFilterChatlist, InputChatlistDialogFilter, ChatInviteAlready
from telethon.tl.types.messages import DialogFilters
from telethon.tl.types.chatlists import ChatlistInvite
from telethon.tl.types.channels import ChannelParticipants
from telethon.tl.functions.messages import GetDialogFiltersRequest, GetFullChatRequest, ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.functions.channels import GetParticipantsRequest, EditAdminRequest, UpdateUsernameRequest
from telethon.tl.functions.chatlists import JoinChatlistInviteRequest, CheckChatlistInviteRequest, LeaveChatlistRequest
from telethon.errors import ChatAdminRequiredError, MessageNotModifiedError, FloodWaitError, UsernameOccupiedError

from app.settings import BASE_DIR, API_ID, API_HASH, USERBOT_PN_LIST, USERBOT_HOST_LIST, MAX_SLEEP_TIME
from bot import models, utils
from bot.types import Log, Limitation, UsernameChangeReason
from bot.utils_lib.stats import get_stats_with_graphs


class App:
    def __init__(self, phone_number: str, host: int, func: int = 0):
        if host:
            name = f'{phone_number}-host-{host}-func-{func}'
            self.n = USERBOT_HOST_LIST.index(phone_number)
        else:
            name = phone_number
            self.n = USERBOT_PN_LIST.index(phone_number)
        self.client = TelegramClient(f'{BASE_DIR}/sessions/{name}', API_ID, API_HASH, receive_updates=func == 1)
        self.phone_number = phone_number
        self.host = host
        self.userbot: models.UserBot | None = None
        self.channels = []
        self.func = func

        self.username = None
        self.first_name = None
        self.last_name = None
        self.user_id = None

    async def init_client_info(self):
        me: types.User = await self.client.get_me()
        self.username = me.username
        self.first_name = me.first_name
        self.last_name = me.last_name
        self.user_id = me.id
        logging.info(f'Initialized {self.phone_number} {self.user_id} {self.first_name} {self.last_name}')

        phone = '+' + me.phone
        if self.phone_number != phone:
            logging.warning(f'Phone number mismatch: specified {self.phone_number}, actual {phone}')
            self.phone_number = phone

    async def start(self):
        # noinspection PyUnresolvedReferences
        await self.client.start(lambda: self.phone_number)
        await self.init_client_info()
        await self.client.get_dialogs()
        if not self.host or self.func == 1:
            await self.refresh_me()
        if self.func == 1:
            self.client.add_event_handler(
                self.update_username_message_handler,
                events.NewMessage(incoming=True, pattern=r'^UPDATE_USERNAME (?P<data>.+)$')
            )
            self.client.add_event_handler(
                self.make_post_message_handler,
                events.NewMessage(incoming=True, pattern=r'^MAKE_POST (?P<data>.+)$')
            )
            self.client.add_event_handler(
                self.publish_post_message_handler,
                events.NewMessage(incoming=True, pattern=r'^PUBLISH_POST (?P<data>.+)$')
            )
        self.userbot = await models.UserBot.objects.aget(phone_number=self.phone_number)

        settings = await models.Settings.objects.aget()

        if self.host:
            if self.func == 1:
                await self.client.run_until_disconnected()
            elif self.func == 2:
                await self.start_jobs(
                    ('join_channels', 60 * 5),
                    ('check_post_deletions', settings.check_post_deletions_interval),
                    ('check_lang_stats', settings.check_stats_interval),
                    ('delete_old_posts', settings.delete_old_posts_interval * 60)
                )
        else:
            await self.start_jobs(
                ('join_channels', 60 * 5),
                ('check_post_views', settings.check_post_views_interval)
            )

    async def start_jobs(self, *jobs: tuple[str, int]):
        await gather(*[self.loop_wrapper(getattr(self, job), interval) for job, interval in jobs])

    async def loop_wrapper(self, func, sleep_time, *args, **kwargs):
        async def wrapper():
            await models.UserBot.objects.filter(user_id=self.user_id).aupdate(ping_time=datetime.now(timezone.utc))
            await func(*args, **kwargs)
        await utils.loop_wrapper(wrapper, sleep_time)

    async def refresh(self):
        async for user in models.UserBot.objects.all():
            if user.phone_number not in USERBOT_HOST_LIST and user.phone_number not in USERBOT_PN_LIST:
                await user.adelete()

        settings = await models.Settings.objects.aget()
        chat_invite_info: ChatInviteAlready = await self.client(CheckChatInviteRequest(settings.userbots_chat_invite))
        await self.client(GetFullChatRequest(chat_invite_info.chat.id))

        if not self.userbot:
            self.userbot = await models.UserBot.objects.aget(phone_number=self.phone_number)
        async for channel in models.Channel.objects.filter(owner=self.userbot):
            peer = await self.client.get_input_entity(channel.v2_id)
            peer = InputChannel(peer.channel_id, peer.access_hash)
            cp: ChannelParticipants = await self.client(
                GetParticipantsRequest(
                    channel=peer,
                    filter=ChannelParticipantsAdmins(),
                    offset=0,
                    limit=100,
                    hash=0
                )
            )
            admins = [admin.user_id for admin in cp.participants]
            async for user in models.UserBot.objects.all():
                if user.phone_number not in USERBOT_HOST_LIST and user.user_id not in admins:
                    privileges = types.TypeChatAdminRights(delete_messages=True, post_messages=True, edit_messages=True, change_info=True)
                    await self.client(EditAdminRequest(channel.v2_id, user.user_id, privileges, ''))
                    logging.info(f'Promoted {user.user_id} to admin in {channel.title}')
                    await sleep(1)

    async def refresh_channel(self, channel: models.Channel):
        channel_api: types.Channel = await self.client.get_entity(channel.v2_id)
        channel.title = channel_api.title
        channel.username = channel_api.username
        channel.has_protected_content = channel_api.noforwards
        await channel.asave()

    async def refresh_me(self):
        await models.UserBot.objects.aupdate_or_create(user_id=self.user_id, defaults={
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
        })

    async def join_channels(self):
        settings = await models.Settings.objects.aget()
        chat_invite_info = await self.client(CheckChatInviteRequest(settings.userbots_chat_invite))
        if not isinstance(chat_invite_info, ChatInviteAlready):
            await self.client(ImportChatInviteRequest(settings.userbots_chat_invite))
        check: ChatlistInvite = await self.client(CheckChatlistInviteRequest(slug=settings.chatlist_invite))
        channels = [channel for channel in check.chats if channel.left]
        if channels:
            # delete old chatlists
            filters: DialogFilters = await self.client(GetDialogFiltersRequest())
            for fil in filters.filters:
                if isinstance(fil, DialogFilterChatlist):
                    await self.client(LeaveChatlistRequest(InputChatlistDialogFilter(fil.id), []))
            # join new chatlist
            await self.client(JoinChatlistInviteRequest(
                slug=settings.chatlist_invite,
                peers=[InputPeerChannel(x.id, x.access_hash) for x in channels],
            ))
            await self.client.get_dialogs()
            logging.info(f'Joined {len(channels)} channels: {", ".join([channel.title for channel in channels])}')

    async def change_username(self, channel: models.Channel, reason, comment, ignore_wait=False):
        for _ in range(3):
            new_username = await utils.rand_username(channel.username)
            logging.info(f'Updating channel {channel.title} username to {new_username}')
            try:
                await self.client(UpdateUsernameRequest(channel.v2_id, new_username))
                channel.username = new_username
                channel.last_username_change = datetime.now(timezone.utc)
                await channel.asave()
                await models.Log.objects.acreate(
                    type=Log.USERNAME_CHANGE,
                    userbot=self.userbot,
                    channel=channel,
                    reason=reason,
                    comment=comment
                )
                return new_username
            except UsernameOccupiedError:
                logging.warning(f'Username {new_username} is occupied')
                await sleep(5)
            except FloodWaitError as e:
                logging.warning(f'Flood wait {e.seconds} seconds')
                await models.Log.objects.acreate(
                    type=Log.USERNAME_CHANGE,
                    userbot=self.userbot,
                    channel=channel,
                    success=False,
                    reason=reason,
                    comment=comment,
                    error_message=str(e)[-256:]
                )
                if not ignore_wait:
                    await sleep(min(e.seconds, MAX_SLEEP_TIME))
            except Exception as e:
                logging.critical(e)
                if not ignore_wait:
                    await sleep(60)

    async def change_username_by_limit(self, channel: models.Channel, reason, comment, events_count: int, events_limit: int):
        now = datetime.now(timezone.utc)
        settings = await models.Settings.objects.aget()
        unlocked = (channel.last_username_change is None or
                    channel.last_username_change < now - timedelta(minutes=settings.username_change_cooldown))
        if not unlocked:
            return
        daily_username_changes_count = await models.Log.objects.filter(
            channel=channel, type=Log.USERNAME_CHANGE, success=True, created__gte=utils.day_start()
        ).acount()
        excess = await models.Excess.objects.filter(
            channel=channel, type=Log.USERNAME_CHANGE, created__gte=utils.day_start()
        ).order_by('-created').afirst()
        daily_exceeded = ((excess.value if excess else 0) + daily_username_changes_count) * events_limit
        if daily_exceeded >= events_count:
            return
        total_exceeded = (events_count - daily_exceeded) // events_limit
        logging.info(f'Daily username changes {daily_username_changes_count}, daily exceeded {daily_exceeded}, total exceeded {total_exceeded}')
        if total_exceeded == 0:
            return
        new_excess = total_exceeded - 1
        if new_excess > 0:
            if excess:
                excess.value += new_excess
                await excess.asave()
            else:
                await models.Excess.objects.acreate(channel=channel, type=Log.USERNAME_CHANGE, value=new_excess)
        return await self.change_username(channel, reason, comment)

    async def get_channels(self, owner=False):
        channels = models.Channel.objects.all()
        if owner:
            channels = channels.filter(owner=self.userbot)
        if (await models.Settings.objects.aget()).individual_allocations:
            channels_count = await channels.acount()
            userbot_count = await models.UserBot.objects.acount()
            if userbot_count <= channels_count:
                channels.query.set_limits(self.n, userbot_count)
            else:
                channels.query.set_limits(self.n % channels_count, 1)
        return channels

    async def check_post_deletions(self):
        now = datetime.now(timezone.utc)
        async for channel in models.Channel.objects.filter(owner=self.userbot):
            await self.refresh_channel(channel)
            daily_deletions_count = await models.Log.objects.filter(
                channel=channel, type=Log.DELETION, success=True,
                created__year=now.year, created__month=now.month, created__day=now.day,
            ).values('post_id').distinct().acount()
            logging.info(f'Checking channel {channel.title} with {daily_deletions_count} daily deletions')
            if channel.deletions_count_for_username_change:
                comment = f'Daily deletions {daily_deletions_count} > limit {channel.deletions_count_for_username_change}'
                await self.change_username_by_limit(channel, UsernameChangeReason.DELETIONS_LIMIT, comment,
                                                    daily_deletions_count, channel.deletions_count_for_username_change)

    async def delete_old_posts(self):
        now = datetime.now(timezone.utc)
        async for channel in models.Channel.objects.filter(delete_posts_after_days__gt=0):
            logging.info(f'Checking channel {channel.title}')
            messages = []
            async for message in self.client.iter_messages(
                channel.v2_id, limit=100,
                offset_date=now - timedelta(days=channel.delete_posts_after_days)
            ):
                messages.append(message.id)
            logging.info(f'Found {len(messages)} messages')
            await self.client.delete_messages(channel.v2_id, messages)
            await sleep(5)

    async def check_post_views(self):
        now = datetime.now(timezone.utc)
        async for channel in await self.get_channels():
            logging.info(f'Checking channel {channel.channel_id}')
            single_messages: list[types.Message] = []
            grouped_messages: dict[int, list[types.Message]] = {}
            limitations = [x async for x in models.Limitation.objects.filter(
                channel=channel, type=Limitation.POST_VIEWS
            ).order_by('-created')]
            async for message in self.client.iter_messages(channel.v2_id):
                message: types.Message
                message.date = message.date.replace(tzinfo=timezone.utc)
                if message.date.date() < now.date() - timedelta(days=channel.history_days_limit):
                    break
                if not message.views:
                    continue
                logging.info(f'Found views {message.views}')
                for limitation in limitations:
                    logging.info(f'Checking limitation {limitation.start} - {limitation.end}, post date {message.date.date()}')
                    if limitation.start <= message.date.date() <= limitation.end:
                        skip = False
                        for lim in limitations:
                            if (
                                lim.start <= message.date.date() <= lim.end and lim.priority < limitation.priority and
                                bool(lim.views) == bool(limitation.views) and
                                bool(lim.views_difference) == bool(limitation.views_difference)
                            ):
                                logging.info(f'Skipping limitation {limitation.start} - {limitation.end} with priority {limitation.priority} '
                                             f'because it is inside {lim.start} - {lim.end} with priority {lim.priority}')
                                skip = True
                                break
                        if skip:
                            continue
                        if limitation.views and message.views > limitation.views:
                            logging.info(f'Found views {message.views} more than limitation {limitation.views}')
                            if message.grouped_id and channel.delete_albums:
                                if message.grouped_id not in grouped_messages:
                                    grouped_messages[message.grouped_id] = await utils.collect_media_group(self.client, message)
                            else:
                                single_messages.append(message)
                        if limitation.views_difference:
                            logging.info(f'Checking views difference {limitation.views_difference}')
                            if post := await models.PostCheck.objects.filter(channel=channel, post_id=message.id).afirst():
                                if post.last_check < now - timedelta(minutes=limitation.views_difference_interval) \
                                        and (message.views - post.views) * 100 / post.views > limitation.views_difference:
                                    logging.info(f'Found views difference {limitation.views_difference}')
                                    if message.grouped_id and channel.delete_albums:
                                        if message.grouped_id not in grouped_messages:
                                            grouped_messages[message.grouped_id] = await utils.collect_media_group(self.client, message)
                                    else:
                                        single_messages.append(message)
                                    post.last_check = now
                                    await post.asave()
                            else:
                                await models.PostCheck.objects.acreate(post_date=message.date, post_id=message.id, views=message.views)

            logging.info(f'Found {len(single_messages)} single messages and {len(grouped_messages)} grouped messages')
            for message in single_messages:
                await models.Log.objects.acreate(
                    type=Log.DELETION,
                    userbot=self.userbot,
                    channel=channel,
                    post_id=message.id,
                    post_date=message.date,
                    post_views=message.views,
                )
                if channel.republish_today_posts and message.date.date() == now.date():
                    if channel.has_protected_content:
                        if isinstance(message.media, MessageMediaPhoto):
                            # noinspection PyTypeChecker
                            photo: BytesIO = await self.client.download_media(message, bytes)
                            await self.client.send_message(channel.v2_id, message.message, file=photo)
                        elif message.message:
                            await self.client.send_message(channel.v2_id, message.message)
                    else:
                        await self.client.send_message(channel.v2_id, message)
                    await sleep(1)
                await self.client.delete_messages(channel.v2_id, message.id)
                await sleep(1)
            for grouped_message in grouped_messages.values():
                await models.Log.objects.acreate(
                    type=Log.DELETION,
                    userbot=self.userbot,
                    channel=channel,
                    post_id=grouped_message[0].id,
                    post_date=grouped_message[0].date,
                    post_views=grouped_message[0].views,
                )
                if channel.republish_today_posts and grouped_message[0].date.date() == now.date():
                    if channel.has_protected_content:
                        # send only first photo from group
                        photo_msgs: list[types.Message] = list(filter(lambda x: x.photo, grouped_message))
                        # noinspection PyTypeChecker
                        photo: BytesIO = await self.client.download_media(photo_msgs[0], bytes) if photo_msgs else None
                        caption_msgs: list[types.Message] = list(filter(lambda x: x.message, grouped_message))
                        caption = caption_msgs[0].message if caption_msgs else ''
                        if photo:
                            await self.client.send_message(channel.v2_id, caption, file=photo)
                        elif caption:
                            await self.client.send_message(channel.v2_id, caption)
                    else:
                        await self.client.send_message(channel.v2_id, grouped_message[0])
                await sleep(1)
                await self.client.delete_messages(channel.v2_id, [message.id for message in grouped_message])
                await sleep(1)

    async def handle_view_limitation(self, channel, current_views, max_views, hourly_distribution):
        if hourly_distribution:
            max_views //= 24 - datetime.now(timezone.utc).hour
        logging.info(f'Views: {current_views}, max views: {max_views}')
        if current_views > max_views:
            comment = f'Views {current_views} > limit {max_views}'
            await self.change_username_by_limit(channel, UsernameChangeReason.LANGUAGE_STATS_VIEWS_LIMIT, comment,
                                                current_views, max_views)
            await sleep(30)
            return True
        return False

    async def handle_view_diff_limitation(self, channel, language, current_views, max_diff, interval):
        if current_views == 0:
            return False
        last_views: models.StatsViews = await models.StatsViews.objects \
            .filter(channel=channel, language=language, created__gte=utils.day_start()) \
            .order_by('-created').afirst()
        logging.info(f'Language: {language}, current views: {current_views}')
        if not last_views:
            last_views = await models.StatsViews.objects.acreate(channel=channel, language=language, value=current_views)
        if last_views.created < datetime.now(timezone.utc) - timedelta(minutes=interval):
            percent_diff = (current_views - last_views.value) * 100 / last_views.value
            logging.info(f'Percent: {percent_diff}, max percent: {max_diff}')
            if percent_diff > max_diff:
                comment = f'Views difference for {language} {percent_diff}% ({last_views.value}|{current_views}) > limit {max_diff}%'
                await self.change_username_by_limit(channel, UsernameChangeReason.LANGUAGE_STATS_VIEWS_DIFFERENCE_LIMIT,
                                                    comment, percent_diff, max_diff)
                await sleep(30)
                return True
        return False

    async def check_lang_stats(self):
        today = datetime.now(timezone.utc).date()
        async for channel in await self.get_channels(owner=True):
            logging.info(f'Checking channel lang stats {channel.title} ({channel.channel_id})')
            try:
                stats, graphs = await get_stats_with_graphs(self.client, channel.v2_id, ['languages_graph'])
            except ChatAdminRequiredError:
                logging.warning(f'Cant get stats for {channel.title}')
                continue
            async for limitation in models.Limitation.objects.filter(
                Q(channel=channel) & Q(type=Limitation.LANGUAGE_STATS) &
                (Q(start_date__lte=today) | Q(start_date=None)) &
                (Q(end_date__gte=today) | Q(end_date=None))
            ).order_by('-created'):
                lang_stats = utils.LanguageStats()
                lang_stats.get_languages_graph_views(graphs, days=1)
                lang_stats.parse_lang_stats_restrictions(limitation.lang_stats_restrictions)
                if limitation.views:
                    if await self.handle_view_limitation(
                            channel,
                            lang_stats.get_total(),
                            limitation.views,
                            limitation.hourly_distribution
                    ):
                        continue
                if limitation.views_difference:
                    if await self.handle_view_diff_limitation(
                            channel,
                            None,
                            lang_stats.get_total(),
                            limitation.views_difference,
                            limitation.views_difference_interval
                    ):
                        continue
                if '*' in lang_stats.restrictions:
                    max_views = lang_stats.restrictions['*']
                    if max_views > 0:
                        if await self.handle_view_limitation(
                                channel,
                                lang_stats.get_others(),
                                max_views,
                                limitation.hourly_distribution
                        ):
                            continue
                    else:  # percentage
                        if await self.handle_view_diff_limitation(
                                channel,
                                '*',
                                lang_stats.get_others(),
                                -max_views,
                                limitation.views_difference_interval
                        ):
                            continue
                for lang, views in lang_stats.get_data().items():
                    if lang not in lang_stats.restrictions:
                        continue
                    max_views = lang_stats.restrictions[lang]
                    if max_views > 0:
                        if await self.handle_view_limitation(
                                channel,
                                views,
                                max_views,
                                limitation.hourly_distribution
                        ):
                            break
                    else:  # percentage
                        if await self.handle_view_diff_limitation(
                                channel,
                                lang,
                                views,
                                -max_views,
                                limitation.views_difference_interval
                        ):
                            break
            await sleep(3)

    async def update_username_message_handler(self, event: Message | events.NewMessage.Event):
        data: dict = json.loads(event.pattern_match['data'])  # {'channel_id': 1}

        channel_id_v2 = data['channel_id']
        channel_id_v1 = abs(int(str(channel_id_v2)[3:]))

        comment = f'Request from {event.sender_id}'
        channel = await database_sync_to_async(models.Channel.objects.get)(channel_id=channel_id_v1)
        username = await self.change_username(channel, UsernameChangeReason.THIRD_PARTY_REQUEST, comment, ignore_wait=True)

        result = json.dumps({'channel_id': channel_id_v2, 'username': username or channel.username})
        await event.respond(f'/update_username {result}')

    async def make_post_message_handler(self, event: Message | events.NewMessage.Event):
        data: dict = json.loads(event.pattern_match['data'])  # {'album_ids': [1, 2, 3], 'text_id': 1, 'bot_user_id': 1}
        settings = await database_sync_to_async(models.Settings.objects.get)()

        album_messages = await self.client.get_messages(settings.archive_channel, ids=data['album_ids']) if data.get('album_ids') else None
        text_message = await self.client.get_messages(settings.archive_channel, ids=data['text_id'])
        result = await self.client.send_message(settings.archive_channel, text_message.message, file=album_messages)

        if isinstance(result, list):
            result_ids = [x.id for x in result]
        else:
            result_ids = [result.id]
        if text_message.entities:
            with suppress(MessageNotModifiedError):
                # noinspection PyTypeChecker
                await self.client.edit_message(
                    settings.archive_channel,
                    result_ids[0],
                    text_message.message,
                    formatting_entities=text_message.entities
                )

        result = json.dumps({'message_ids': result_ids, 'bot_user_id': data['bot_user_id']})
        await event.respond(f'/make_post {result}')

    async def publish_post_message_handler(self, event: Message | events.NewMessage.Event):
        data: dict = json.loads(event.pattern_match['data'])  # {'message_ids': [1, 2, 3], 'channel_id': 1, 'ad_id': 1}
        settings = await database_sync_to_async(models.Settings.objects.get)()

        messages = await self.client.get_messages(settings.archive_channel, ids=data['message_ids'])
        result = await self.client.send_message(data['channel_id'], messages[0].message, file=messages if messages[0].media else None)

        if isinstance(result, list):
            result_ids = [x.id for x in result]
        else:
            result_ids = [result.id]
        if messages[0].entities:
            with suppress(MessageNotModifiedError):
                # noinspection PyTypeChecker
                await self.client.edit_message(
                    data['channel_id'],
                    result_ids[0],
                    messages[0].message,
                    formatting_entities=messages[0].entities
                )

        result = json.dumps({'message_ids': result_ids, 'ad_id': data['ad_id']})
        await event.respond(f'/publish_post {result}')
