import logging
import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
from asyncio import sleep, get_event_loop, gather

from channels.db import database_sync_to_async
from preferences import preferences

from telethon import TelegramClient, types, events
from telethon.types import ChannelParticipantsAdmins, InputPeerChannel, InputChannel, MessageMediaPhoto
from telethon.tl.custom import Message
from telethon.tl.types.chatlists import ChatlistInvite
from telethon.tl.types.channels import ChannelParticipants
from telethon.tl.functions.channels import GetParticipantsRequest, EditAdminRequest, UpdateUsernameRequest
from telethon.tl.functions.chatlists import JoinChatlistInviteRequest, CheckChatlistInviteRequest
from telethon.errors.rpcerrorlist import ChatAdminRequiredError

from app.settings import BASE_DIR, API_ID, API_HASH, USERBOT_PN_LIST, USERBOT_HOST_LIST
from bot import models, utils
from bot.utils_lib.stats import get_stats_with_graphs


class App:
    def __init__(self, phone_number: str, host: int, func: int):
        if host:
            name = f'{phone_number}-host-{host}-func-{func}'
            self.n = USERBOT_HOST_LIST.index(phone_number)
        else:
            name = phone_number
            self.n = USERBOT_PN_LIST.index(phone_number)
        self.client = TelegramClient(f'{BASE_DIR}/sessions/{name}', API_ID, API_HASH, receive_updates=host == 0)
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
        if self.host:
            if self.func == 1:
                await self.refresh()
                await self.client.run_until_disconnected()
            elif self.func == 2:
                await self.start_jobs(
                    ('join_channels', 60 * 5),
                    ('check_post_deletions', preferences.Settings.check_post_deletions_interval),
                    ('check_lang_stats', preferences.Settings.check_stats_interval),
                    ('delete_old_posts', preferences.Settings.delete_old_posts_interval * 60)
                )
        else:
            await self.start_jobs(
                ('join_channels', 60 * 5),
                ('check_post_views', preferences.Settings.check_post_views_interval)
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

        async for channel in models.Channel.objects.all():
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
                if user.user_id not in admins:
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
        check: ChatlistInvite = await self.client(CheckChatlistInviteRequest(slug=preferences.Settings.chatlist_invite))
        channels = [channel for channel in check.chats if channel.left]
        if channels:
            await self.client(JoinChatlistInviteRequest(
                slug=preferences.Settings.chatlist_invite,
                peers=[InputPeerChannel(x.id, x.access_hash) for x in channels],
            ))
            logging.info(f'Joined {len(channels)} channels: {", ".join([channel.title for channel in channels])}')

    async def change_username(self, channel: models.Channel):
        for _ in range(3):
            new_username = utils.rand_username(channel.username)
            logging.info(f'Updating channel {channel.title} username to {new_username}')
            try:
                await self.client(UpdateUsernameRequest(channel.v2_id, new_username))
                channel.username = new_username
                channel.last_username_change = datetime.now(timezone.utc)
                await channel.asave()
                await models.Log.objects.acreate(type=models.types.Log.USERNAME_CHANGE, userbot=self.userbot, channel=channel)
                return new_username
            except Exception as e:
                await models.Log.objects.acreate(type=models.types.Log.USERNAME_CHANGE, userbot=self.userbot, channel=channel, success=False)
                logging.error(e)
                await sleep(5)

    async def get_channels(self):
        channels = models.Channel.objects.all()
        if preferences.Settings.individual_allocations:
            channels_count = await channels.acount()
            userbot_count = await models.UserBot.objects.acount()
            if userbot_count <= channels_count:
                channels.query.set_limits(self.n, userbot_count)
            else:
                channels.query.set_limits(self.n % channels_count, 1)
        return channels

    async def check_post_deletions(self):
        now = datetime.now(timezone.utc)
        async for channel in models.Channel.objects.all():
            await self.refresh_channel(channel)
            daily_deletions_count = await models.Log.objects.filter(
                channel=channel, type=models.types.Log.DELETION, success=True,
                created__year=now.year, created__month=now.month, created__day=now.day,
            ).acount()
            logging.info(f'Checking channel {channel.title} with {daily_deletions_count} daily deletions')
            if (
                    channel.deletions_count_for_username_change and
                    await utils.can_change_username(channel, daily_deletions_count, channel.deletions_count_for_username_change)
            ):
                await self.change_username(channel)

    async def delete_old_posts(self):
        now = datetime.now(timezone.utc)
        async for channel in models.Channel.objects.all():
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
            limitations = [x async for x in models.Limitation.objects.filter(channel=channel).order_by('-created')]
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
                                bool(lim.views_for_deletion) == bool(limitation.views_for_deletion) and
                                bool(lim.views_difference_for_deletion) == bool(limitation.views_difference_for_deletion)
                            ):
                                logging.info(f'Skipping limitation {limitation.start} - {limitation.end} with priority {limitation.priority} '
                                             f'because it is inside {lim.start} - {lim.end} with priority {lim.priority}')
                                skip = True
                                break
                        if skip:
                            continue
                        if limitation.views_for_deletion and message.views > limitation.views_for_deletion:
                            logging.info(f'Found views {message.views} more than limitation {limitation.views_for_deletion}')
                            if message.grouped_id and channel.delete_albums:
                                if message.grouped_id not in grouped_messages:
                                    grouped_messages[message.grouped_id] = await utils.collect_media_group(self.client, message)
                            else:
                                single_messages.append(message)
                        if limitation.views_difference_for_deletion:
                            logging.info(f'Checking views difference {limitation.views_difference_for_deletion}')
                            if post := await models.PostCheck.objects.filter(channel=channel, post_id=message.id).afirst():
                                if post.last_check < now - timedelta(minutes=limitation.views_difference_for_deletion_interval) \
                                        and (message.views - post.views) * 100 / post.views > limitation.views_difference_for_deletion:
                                    logging.info(f'Found views difference {limitation.views_difference_for_deletion}')
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
                    type=models.types.Log.DELETION,
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
                    type=models.types.Log.DELETION,
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
        if current_views > max_views and await utils.can_change_username(channel, current_views, max_views):
            await self.change_username(channel)
            await sleep(30)
            return True
        return False

    async def handle_view_diff_limitation(self, channel, language, current_views, max_diff, interval):
        last_views: models.StatsViews = await models.StatsViews.objects \
            .filter(channel=channel, language=language, created__gte=utils.day_start()) \
            .order_by('-created').afirst()
        logging.info(f'Language: {language}, current views: {current_views}')
        if not last_views:
            last_views = await models.StatsViews.objects.acreate(channel=channel, language=language, value=current_views)
        if last_views.created < datetime.now(timezone.utc) - timedelta(minutes=interval):
            percent_diff = (current_views - last_views.value) * 100 / last_views.value
            logging.info(f'Percent: {percent_diff}, max percent: {max_diff}')
            if percent_diff > max_diff and await utils.can_change_username(channel, percent_diff, max_diff):
                await self.change_username(channel)
                await sleep(30)
                return True
        return False

    async def check_lang_stats(self):
        async for channel in await self.get_channels():
            logging.info(f'Checking channel lang stats {channel.title} ({channel.channel_id})')
            try:
                stats, graphs = await get_stats_with_graphs(self.client, channel.v2_id, ['languages_graph'])
            except ChatAdminRequiredError:
                logging.error(f'Cant get stats for {channel.title}')
                continue
            async for limitation in models.Limitation.objects.filter(channel=channel).order_by('-created'):
                if not limitation.lang_stats_restrictions:
                    continue
                lang_stats = utils.LanguageStats()
                lang_stats.get_languages_graph_views(graphs, days=1)
                lang_stats.parse_lang_stats_restrictions(limitation.lang_stats_restrictions)
                if limitation.views_for_deletion:
                    if await self.handle_view_limitation(
                            channel,
                            lang_stats.get_total(),
                            limitation.views_for_deletion,
                            limitation.hourly_distribution
                    ):
                        continue
                if limitation.views_difference_for_deletion:
                    if await self.handle_view_diff_limitation(
                            channel,
                            None,
                            lang_stats.get_total(),
                            limitation.views_difference_for_deletion,
                            limitation.views_difference_for_deletion_interval
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
                                limitation.views_difference_for_deletion_interval
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
                                limitation.views_difference_for_deletion_interval
                        ):
                            break
            await sleep(3)

    async def update_username_message_handler(self, event: Message | events.NewMessage.Event):
        data = json.loads(event.pattern_match['data'])

        channel_id_v2 = data['channel_id']
        channel_id_v1 = abs(int(str(channel_id_v2)[3:]))

        channel = await database_sync_to_async(models.Channel.objects.get)(channel_id=channel_id_v1)
        username = await self.change_username(channel)

        result = json.dumps({'channel_id': channel_id_v2, 'username': username or channel.username})
        await event.respond(f'/update_username {result}')

    async def make_post_message_handler(self, event: Message | events.NewMessage.Event):
        data: dict = json.loads(event.pattern_match['data'])  # {'album_ids': [1, 2, 3], 'text_id': 1, 'bot_user_id': 1}

        album_messages = await self.client.get_messages(preferences.Settings.archive_channel, ids=data['album_ids']) if data.get('album_ids') else None
        text_message = await self.client.get_messages(preferences.Settings.archive_channel, ids=data['text_id'])
        result = await self.client.send_message(preferences.Settings.archive_channel, text_message.message, file=album_messages)

        if isinstance(result, list):
            result_ids = [x.id for x in result]
        else:
            result_ids = [result.id]
        if text_message.entities:
            # noinspection PyTypeChecker
            await self.client.edit_message(
                preferences.Settings.archive_channel,
                result_ids[0],
                text_message.message,
                formatting_entities=text_message.entities
            )

        result = json.dumps({'message_ids': result_ids, 'bot_user_id': data['bot_user_id']})
        await event.respond(f'/make_post {result}')

    async def publish_post_message_handler(self, event: Message | events.NewMessage.Event):
        data: dict = json.loads(event.pattern_match['data'])  # {'message_ids': [1, 2, 3], 'channel_id': 1, 'ad_id': 1}

        messages = await self.client.get_messages(preferences.Settings.archive_channel, ids=data['message_ids'])
        result = await self.client.send_message(data['channel_id'], messages[0].message, file=messages if messages[0].media else None)

        if isinstance(result, list):
            result_ids = [x.id for x in result]
        else:
            result_ids = [result.id]
        if messages[0].entities:
            # noinspection PyTypeChecker
            await self.client.edit_message(
                data['channel_id'],
                result_ids[0],
                messages[0].message,
                formatting_entities=messages[0].entities
            )

        result = json.dumps({'message_ids': result_ids, 'ad_id': data['ad_id']})
        await event.respond(f'/publish_post {result}')


def main(number, host=0, func=0):
    utils.init_logger(number)
    app = App(number, host, func)
    get_event_loop().run_until_complete(app.start())
