import logging
import json
from io import BytesIO
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from asyncio import sleep

from django.db.models import Q
from channels.db import database_sync_to_async

from telethon import TelegramClient, types, events
from telethon.sessions import StringSession
from telethon.types import InputPeerChannel, MessageMediaPhoto
from telethon.tl.custom import Message
from telethon.tl.types import DialogFilterChatlist, InputChatlistDialogFilter, ChatInviteAlready, AccountDaysTTL
from telethon.tl.types.messages import DialogFilters, Chats
from telethon.tl.types.chatlists import ChatlistInvite
from telethon.tl.functions.account import UpdateStatusRequest, SetAccountTTLRequest, SetAuthorizationTTLRequest
from telethon.tl.functions.messages import GetDialogFiltersRequest, ImportChatInviteRequest, CheckChatInviteRequest, GetFullChatRequest
from telethon.tl.functions.channels import EditAdminRequest, UpdateUsernameRequest, GetAdminedPublicChannelsRequest
from telethon.tl.functions.chatlists import JoinChatlistInviteRequest, CheckChatlistInviteRequest, LeaveChatlistRequest
from telethon.errors import ChatAdminRequiredError, MessageNotModifiedError, FloodWaitError, UsernameOccupiedError
from telethon.errors.rpcerrorlist import FreshResetAuthorisationForbiddenError

from app.settings import API_ID, API_HASH, MAX_SLEEP_TIME
from bot import models, utils
from bot.types import LogType, LimitationType, LimitationAction, UsernameChangeReason, StatsViewsType, SessionMode
from bot.utils_lib.stats import get_stats_with_graphs
from bot.conversions import (
    limitation_action__log_type as la__lt,
    limitation_type__stats_views as lt__sv,
    stats_views__username_change_reason as sv__ucr,
    stats_views__username_change_reason_diff as sv_ucr_diff,
)


class App:
    def __init__(self, session: models.UserBotSession):
        self.session = session
        self.userbot = session.userbot

        self.n = 0
        self.worker_sessions_count = 0

        self.client = TelegramClient(
            StringSession(session.authorization),
            API_ID,
            API_HASH,
            receive_updates=session.mode == SessionMode.LISTENER
        )

    async def start(self):
        await self.run_until_disconnected()

    async def run_until_disconnected(self):
        # first database access should be under sync_to_async to close old connections
        settings = await database_sync_to_async(models.Settings.objects.get)()

        # noinspection PyUnresolvedReferences
        await self.client.start(self.userbot.phone_number)
        await self.update_entities()
        await self.init_client_info()

        if self.session.mode == SessionMode.LISTENER:
            await self.setup_account()
            await self.refresh_channels()
            await self.refresh_owned_channels()

            self.client.add_event_handler(
                self.bot_action_handler,
                events.NewMessage(incoming=True, pattern=r'^ACTION (?P<data>.+)$')
            )
            self.client.add_event_handler(
                self.service_message_handler,
                events.NewMessage(777000, func=lambda e: e.message.message, incoming=True)
            )
            # noinspection PyUnresolvedReferences
            await self.client.run_until_disconnected()
            return

        await self.start_jobs(
            ('switch_offline', 60),
            ('update_entities', 60 * 5),
            ('join_channels', 60 * 5),
            ('refresh_channels', 60 * 5),
            ('refresh_admins', 60 * 5),
            ('check_stats', settings.check_stats_interval),
            ('check_post_views', settings.check_post_views_interval),
            ('check_post_deletions', settings.check_post_deletions_interval),
            ('delete_old_posts', settings.delete_old_posts_interval * 60)
        )

    async def start_jobs(self, *jobs: tuple[str, int]):
        await utils.gather_coroutines([self.loop_wrapper(getattr(self, job), interval) for job, interval in jobs])

    async def loop_wrapper(self, func, sleep_time, *args, **kwargs):
        async def wrapper():
            self.session.ping_time = datetime.now(timezone.utc)
            await self.session.asave()
            await func(*args, **kwargs)
        await utils.loop_wrapper(wrapper, sleep_time)

    async def init_client_info(self):
        me: types.User = await self.client.get_me()
        self.userbot.username = me.username
        self.userbot.first_name = me.first_name
        self.userbot.last_name = me.last_name
        self.userbot.user_id = me.id
        logging.info(f'Initialized {self.userbot.phone_number} {self.userbot.user_id} {self.userbot.fullname}')

        if self.userbot.phone_number != me.phone:
            logging.warning(f'Phone number mismatch: specified {self.userbot.phone_number}, actual {me.phone}')
            self.userbot.phone_number = me.phone

        await self.userbot.asave()

        if self.session.mode == SessionMode.LISTENER:
            return

        active_numbers = [x.phone_number async for x in models.UserBotConfig.objects.filter(is_active=True)]

        session_ids = [x.id async for x in models.UserBotSession.objects
                       .filter(mode=SessionMode.WORKER, userbot__phone_number__in=active_numbers)
                       .order_by('id')]

        logging.info(f'Session IDs: {session_ids}')

        self.worker_sessions_count = len(session_ids)
        self.n = session_ids.index(self.session.id)

        logging.info(f'Session number {self.n} of {self.worker_sessions_count}')

    async def update_entities(self):
        settings = await models.Settings.objects.aget()

        await self.client.get_dialogs()

        chat_invite_info: ChatInviteAlready = await self.client(CheckChatInviteRequest(settings.userbots_chat_invite))
        await self.client(GetFullChatRequest(chat_invite_info.chat.id))

    async def refresh_admins(self):
        users = [session.userbot async for session in models.UserBotSession.objects
                 .filter(mode=SessionMode.WORKER)
                 .select_related('userbot')
                 if session.userbot.user_id != self.userbot.user_id]

        channels = [x async for x in models.Channel.objects.filter(owner=self.userbot)]

        for channel in channels:
            for user in users:
                privileges = types.TypeChatAdminRights(
                    delete_messages=True,
                    post_messages=True,
                    edit_messages=True,
                    change_info=True
                )
                # noinspection PyTypeChecker
                await self.client(EditAdminRequest(channel.v2_id, user.user_id, privileges, ''))
                logging.info(f'Promoted {user.fullname} to admin in {channel.title}')
                await sleep(1)

    async def refresh_channel(self, channel: models.Channel):
        channel_api: types.Channel = await self.client.get_entity(channel.v2_id)
        channel.title = channel_api.title
        channel.username = channel_api.username
        channel.has_protected_content = channel_api.noforwards
        await channel.asave()

    async def refresh_channels(self):
        async for channel in models.Channel.objects.all():
            await self.refresh_channel(channel)

    async def refresh_owned_channels(self):
        db_channels = [x async for x in models.Channel.objects.all()]
        own_channels: Chats = await self.client(GetAdminedPublicChannelsRequest())
        own_channels_ids = [x.id for x in own_channels.chats]

        channels = [x for x in db_channels if x.channel_id in own_channels_ids]
        logging.info(f'Own channels: {channels}')

        for channel in channels:
            channel.owner = self.userbot

        await models.Channel.objects.abulk_update(channels, ['owner'])

    async def setup_account(self):
        await self.client(SetAccountTTLRequest(ttl=AccountDaysTTL(days=720)))

        with suppress(FreshResetAuthorisationForbiddenError):
            await self.client(SetAuthorizationTTLRequest(authorization_ttl_days=360))

    async def switch_offline(self):
        await self.client(UpdateStatusRequest(offline=False))
        await sleep(1)
        await self.client(UpdateStatusRequest(offline=True))

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

    async def change_username(
            self,
            channel: models.Channel,
            reason: UsernameChangeReason,
            limitation: models.Limitation,
            comment: str,
            ignore_wait=False,
    ):
        sl = (await models.Settings.objects.aget()).username_suffix_length or 1
        for _ in range(3):
            new_username = utils.rand_username(channel.username, sl)
            logging.info(f'Updating channel {channel.title} username to {new_username}')
            try:
                await self.client(UpdateUsernameRequest(channel.v2_id, new_username))
                channel.username = new_username
                channel.last_username_change = datetime.now(timezone.utc)
                await channel.asave()
                await models.Log.objects.acreate(
                    type=LogType.USERNAME_CHANGE,
                    userbot=self.userbot,
                    channel=channel,
                    reason=reason,
                    limitation=limitation,
                    comment=comment
                )
                return new_username
            except UsernameOccupiedError:
                logging.warning(f'Username {new_username} is occupied')
                await sleep(5)
            except FloodWaitError as e:
                logging.warning(f'Flood wait {e.seconds} seconds')
                await models.Log.objects.acreate(
                    type=LogType.USERNAME_CHANGE,
                    userbot=self.userbot,
                    channel=channel,
                    success=False,
                    reason=reason,
                    limitation=limitation,
                    comment=comment,
                    error_message=str(e)[-256:]
                )
                if not ignore_wait:
                    await sleep(min(e.seconds, MAX_SLEEP_TIME))
                return None
            except Exception as e:
                logging.critical(e)
                if not ignore_wait:
                    await sleep(60)
        return None

    async def change_username_by_limit(
            self,
            channel: models.Channel,
            reason: UsernameChangeReason,
            comment: str,
            events_count: int,
            events_limit: int,
            limitation: models.Limitation = None,
    ):
        if not await utils.is_username_change_unlocked(channel):
            return

        # Count successful username changes made today
        daily_username_changes_count = await models.Log.objects.filter(
            channel=channel,
            type=LogType.USERNAME_CHANGE,
            reason=reason,
            success=True,
            created__gte=utils.day_start(),
        ).acount()

        # Get any excess username changes from previous calculations
        excess = await models.Excess.objects.filter(
            channel=channel,
            type=LogType.USERNAME_CHANGE,
            reason=reason,
            created__gte=utils.day_start(),
        ).order_by('-created').afirst()

        # Calculate events consumed by username changes
        events_consumed = ((excess.value if excess else 0) + daily_username_changes_count) * events_limit

        # Check if we've already consumed all available events
        if events_consumed >= events_count:
            return

        # Calculate how many username changes we can afford with remaining events
        allowed_username_changes = (events_count - events_consumed) // events_limit

        logging.info(
            f'Daily username changes: {daily_username_changes_count}, '
            f'events consumed: {events_consumed}, '
            f'allowed changes: {allowed_username_changes}'
        )

        # If we can't afford even one username change, exit
        if allowed_username_changes == 0:
            return

        # We're about to perform 1 username change, so calculate the excess
        new_excess = allowed_username_changes - 1

        if new_excess > 0:
            if excess:
                excess.value += new_excess
                await excess.asave()
            else:
                await models.Excess.objects.acreate(
                    channel=channel,
                    type=LogType.USERNAME_CHANGE,
                    reason=reason,
                    value=new_excess,
                )

        await utils.send_username_change_request(self.client, channel, limitation, reason, comment)

    async def get_channels(self, **kwargs):
        channels = models.Channel.objects.filter(**kwargs).order_by('channel_id').select_related('owner')
        if (await models.Settings.objects.aget()).individual_allocations:
            channels_count = await channels.acount()
            if channels_count == 0 or self.worker_sessions_count == 0:
                return []
            if self.worker_sessions_count <= channels_count:
                # split channels as evenly as possible between bots
                low = (self.n * channels_count) // self.worker_sessions_count
                high = ((self.n + 1) * channels_count) // self.worker_sessions_count
            else:
                # more bots than channels: assign one channel per bot, cycling
                low = self.n % channels_count
                high = low + 1
            channels.query.set_limits(low, high)
        results = [x async for x in channels]
        logging.info(f'Requested channels: {results}')
        return results

    async def check_post_deletions(self):
        now = datetime.now(timezone.utc)
        channels = await self.get_channels(deletions_count_for_username_change__gt=0)
        for channel in channels:
            daily_deletions_count = await models.Log.objects.filter(
                channel=channel, type=LogType.DELETION, success=True,
                created__year=now.year, created__month=now.month, created__day=now.day,
            ).values('post_id').distinct().acount()
            logging.info(f'Checking channel {channel.title} with {daily_deletions_count} daily deletions')
            comment = f'Daily deletions {daily_deletions_count} > limit {channel.deletions_count_for_username_change}'
            await self.change_username_by_limit(channel, UsernameChangeReason.DELETIONS_LIMIT, comment,
                                                daily_deletions_count, channel.deletions_count_for_username_change)

    async def delete_old_posts(self):
        now = datetime.now(timezone.utc)
        channels = await self.get_channels(delete_posts_after_days__gt=0)
        for channel in channels:
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
        channels = await self.get_channels(limitations__type=LimitationType.POST_VIEWS)
        chunk, offset = 5, 0
        while offset < len(channels):
            await utils.gather_coroutines([
                self.check_channel_post_views(channel)
                for channel in channels[offset:offset + chunk]
            ])
            offset += chunk

    async def check_channel_post_views(self, channel: models.Channel):
        now = datetime.now(timezone.utc)
        logging.info(f'Checking channel {channel.title}')
        single_messages: list[utils.MessageData] = []
        grouped_messages: dict[int, utils.MessageData] = {}
        limitations = [x async for x in channel.limitations
                       .filter(type=LimitationType.POST_VIEWS)
                       .order_by('-created')]
        logged_ids = {x.limitation_id async for x in models.Log.objects
                      .filter(channel=channel, created__gte=utils.day_start(), limitation__isnull=False)}
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
                    if not utils.is_limitation_highest(limitation, limitations, message.date.date()):
                        continue
                    if not utils.is_limitation_activated(limitation, limitations, logged_ids):
                        continue
                    if limitation.views and message.views > limitation.views:
                        logging.info(f'Found views {message.views} more than limitation {limitation.views}')
                        if message.grouped_id and channel.delete_albums:
                            if message.grouped_id not in grouped_messages:
                                media_group = await utils.collect_media_group(self.client, message)
                                grouped_messages[message.grouped_id] = utils.MessageData(limitation, media_group=media_group)
                        else:
                            single_messages.append(utils.MessageData(limitation, message))
                    if limitation.views_difference:
                        logging.info(f'Checking views difference {limitation.views_difference}')
                        if post := await models.PostCheck.objects.filter(channel=channel, post_id=message.id).afirst():
                            if post.last_check < now - timedelta(minutes=limitation.views_difference_interval) \
                                    and (message.views - post.views) * 100 / post.views > limitation.views_difference:
                                logging.info(f'Found views difference {limitation.views_difference}')
                                if message.grouped_id and channel.delete_albums:
                                    if message.grouped_id not in grouped_messages:
                                        media_group = await utils.collect_media_group(self.client, message)
                                        grouped_messages[message.grouped_id] = utils.MessageData(limitation, media_group=media_group)
                                else:
                                    single_messages.append(utils.MessageData(limitation, message))
                                post.last_check = now
                                await post.asave()
                        else:
                            await models.PostCheck.objects.acreate(post_date=message.date, post_id=message.id, views=message.views)

        logging.info(f'Found {len(single_messages)} single messages and {len(grouped_messages)} grouped messages')

        username_changed = False

        for s_message in single_messages:
            await models.Log.objects.acreate(
                type=la__lt[s_message.limitation.type],
                userbot=self.userbot,
                channel=channel,
                limitation=s_message.limitation,
                post_id=s_message.message.id,
                post_date=s_message.message.date,
                post_views=s_message.message.views,
            )
            if s_message.limitation.action == LimitationAction.CHANGE_USERNAME:
                if not username_changed:
                    await utils.send_username_change_request(
                        self.client,
                        channel,
                        s_message.limitation,
                        UsernameChangeReason.DELETIONS_LIMIT
                    )
                continue
            if channel.republish_today_posts and s_message.message.date.date() == now.date():
                if channel.has_protected_content:
                    if isinstance(s_message.message.media, MessageMediaPhoto):
                        # noinspection PyTypeChecker
                        photo: BytesIO = await self.client.download_media(s_message.message, bytes)
                        await self.client.send_message(channel.v2_id, s_message.message.message, file=photo)
                    elif s_message.message.message:
                        await self.client.send_message(channel.v2_id, s_message.message.message)
                else:
                    await self.client.send_message(channel.v2_id, s_message.message)
                await sleep(1)
            await self.client.delete_messages(channel.v2_id, s_message.message.id)
            await sleep(1)
        for g_message in grouped_messages.values():
            max_post_views = max(g_message.media_group, key=lambda x: x.views).views
            await models.Log.objects.acreate(
                type=la__lt[g_message.limitation.type],
                userbot=self.userbot,
                channel=channel,
                limitation=g_message.limitation,
                post_id=g_message.media_group[0].id,
                post_date=g_message.media_group[0].date,
                post_views=max_post_views,
            )
            if g_message.limitation.action == LimitationAction.CHANGE_USERNAME:
                if not username_changed:
                    await utils.send_username_change_request(
                        self.client,
                        channel,
                        g_message.limitation,
                        UsernameChangeReason.DELETIONS_LIMIT
                    )
                continue
            if channel.republish_today_posts and g_message.media_group[0].date.date() == now.date():
                if channel.has_protected_content:
                    # send only first photo from group
                    photo_msgs: list[types.Message] = list(filter(lambda x: x.photo, g_message.media_group))
                    # noinspection PyTypeChecker
                    photo: BytesIO = await self.client.download_media(photo_msgs[0], bytes) if photo_msgs else None
                    caption_msgs: list[types.Message] = list(filter(lambda x: x.message, g_message.media_group))
                    caption = caption_msgs[0].message if caption_msgs else ''
                    if photo:
                        await self.client.send_message(channel.v2_id, caption, file=photo)
                    elif caption:
                        await self.client.send_message(channel.v2_id, caption)
                else:
                    await self.client.send_message(channel.v2_id, g_message.media_group[0])
            await sleep(1)
            await self.client.delete_messages(channel.v2_id, [message.id for message in g_message.media_group])
            await sleep(1)

    async def handle_view_limitation(
            self,
            channel: models.Channel,
            limitation: models.Limitation,
            sv_type: StatsViewsType,
            current_views: int,
            max_views: int,
            hourly_distribution: bool,
    ):
        if hourly_distribution:
            max_views //= 24 - datetime.now(timezone.utc).hour
        logging.info(f'Views: {current_views}, max views: {max_views}')
        if current_views > max_views:
            comment = f'Views {current_views} > limit {max_views}'
            await self.change_username_by_limit(
                channel,
                sv__ucr[sv_type],
                comment,
                current_views,
                max_views,
                limitation=limitation
            )
            await sleep(30)
            return True
        return False

    async def handle_view_diff_limitation(
            self,
            channel: models.Channel,
            limitation: models.Limitation,
            sv_type: StatsViewsType,
            key: str | None,
            current_views: int,
            max_diff: int,
            interval: int,
    ):
        if current_views == 0:
            return False
        last_views: models.StatsViews = await models.StatsViews.objects \
            .filter(channel=channel, type=sv_type, key=key, created__gte=utils.day_start()) \
            .order_by('-created').afirst()
        logging.info(f'Key: {key}, current views: {current_views}')
        if not last_views:
            last_views = await models.StatsViews.objects.acreate(channel=channel, type=sv_type, key=key, value=current_views)
        if last_views.created < datetime.now(timezone.utc) - timedelta(minutes=interval):
            percent_diff = (current_views - last_views.value) * 100 / last_views.value
            logging.info(f'Percent: {percent_diff}, max percent: {max_diff}')
            if percent_diff > max_diff:
                comment = f'Views difference for {key} {percent_diff}% ({last_views.value}|{current_views}) > limit {max_diff}%'
                await self.change_username_by_limit(
                    channel,
                    sv_ucr_diff[sv_type],
                    comment,
                    percent_diff,
                    max_diff,
                    limitation=limitation
                )
                await sleep(30)
                return True
        return False

    async def check_stats(self):
        limitation_types = [LimitationType.LANGUAGE_STATS, LimitationType.VIEWS_BY_SOURCE_STATS]
        channels = await self.get_channels(limitations__type__in=limitation_types)
        today = utils.day_start()
        for channel in channels:
            logging.info(f'Checking channel stats {channel.title} ({channel.channel_id})')
            try:
                stats, graphs = await get_stats_with_graphs(self.client, channel.v2_id, ['languages_graph', 'views_by_source_graph'])
            except ChatAdminRequiredError:
                logging.warning(f'Cant get stats for {channel.title}')
                continue
            logged_ids = {x.limitation_id async for x in models.Log.objects
                          .filter(channel=channel, created__gte=today, limitation__isnull=False)}
            for graph_index, limitation_type in enumerate(limitation_types):
                limitations = [x async for x in channel.limitations.filter(
                    Q(channel=channel) & Q(type=limitation_type) &
                    (Q(start_date__lte=today) | Q(start_date=None)) &
                    (Q(end_date__gte=today) | Q(end_date=None))
                ).order_by('-created')]
                for limitation in limitations:
                    if not utils.is_limitation_highest(limitation, limitations, today.date()):
                        continue
                    if not utils.is_limitation_activated(limitation, limitations, logged_ids):
                        continue
                    stats_data = utils.StatsHandler()
                    stats_data.get_graph_views(graphs[graph_index], days=1)
                    stats_data.parse_stats_restrictions(limitation.stats_restrictions)
                    if limitation.views:
                        if await self.handle_view_limitation(
                                channel,
                                limitation,
                                lt__sv[limitation_type],
                                stats_data.get_total(),
                                limitation.views,
                                limitation.hourly_distribution
                        ):
                            continue
                    if limitation.views_difference:
                        if await self.handle_view_diff_limitation(
                                channel,
                                limitation,
                                lt__sv[limitation_type],
                                None,
                                stats_data.get_total(),
                                limitation.views_difference,
                                limitation.views_difference_interval
                        ):
                            continue
                    if '*' in stats_data.restrictions:
                        max_views = stats_data.restrictions['*']
                        if max_views > 0:
                            if await self.handle_view_limitation(
                                    channel,
                                    limitation,
                                    lt__sv[limitation_type],
                                    stats_data.get_others(),
                                    max_views,
                                    limitation.hourly_distribution
                            ):
                                continue
                        else:  # percentage
                            if await self.handle_view_diff_limitation(
                                    channel,
                                    limitation,
                                    lt__sv[limitation_type],
                                    '*',
                                    stats_data.get_others(),
                                    -max_views,
                                    limitation.views_difference_interval
                            ):
                                continue
                    for key, views in stats_data.get_data().items():
                        if key not in stats_data.restrictions:
                            continue
                        max_views = stats_data.restrictions[key]
                        if max_views > 0:
                            if await self.handle_view_limitation(
                                    channel,
                                    limitation,
                                    lt__sv[limitation_type],
                                    views,
                                    max_views,
                                    limitation.hourly_distribution
                            ):
                                break
                        else:  # percentage
                            if await self.handle_view_diff_limitation(
                                    channel,
                                    limitation,
                                    lt__sv[limitation_type],
                                    key,
                                    views,
                                    -max_views,
                                    limitation.views_difference_interval
                            ):
                                break
            await sleep(3)

    async def bot_action_handler(self, event: Message | events.NewMessage.Event):
        data: dict = json.loads(event.pattern_match['data'])  # {'action': 'update_username', ...}

        response = None

        match data['action']:
            case 'update_username':
                response = await self.update_username_message_handler(data, event.sender_id)
            case 'make_post':
                response = await self.make_post_message_handler(data)
            case 'publish_post':
                response = await self.publish_post_message_handler(data)
            case _:
                logging.error(f'Unknown action {data['action']}')

        if response:
            await event.respond(response)

    async def update_username_message_handler(self, data: dict, sender: int):  # {'channel_id': 1}
        channel_id_v2 = data['channel_id']
        channel_id_v1 = abs(int(str(channel_id_v2)[3:]))

        reason = data.get('reason') or UsernameChangeReason.THIRD_PARTY_REQUEST
        comment = data.get('comment') or f'Request from {sender}'
        limitation_id = data.get('limitation_id')
        limitation = None
        username = None

        channel = await database_sync_to_async(models.Channel.objects.select_related('owner').get)(channel_id=channel_id_v1)

        if limitation_id:
            limitation = await models.Limitation.objects.aget(id=int(limitation_id))

        if await utils.is_username_change_unlocked(channel):
            username = await self.change_username(channel, reason, limitation, comment, ignore_wait=True)

        result = json.dumps({'channel_id': channel_id_v2, 'username': username or channel.username})
        return f'/update_username {result}'

    async def make_post_message_handler(self, data: dict):  # {'album_ids': [1, 2, 3], 'text_id': 1, 'bot_user_id': 1}
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
                await self.client.edit_message(
                    settings.archive_channel,
                    result_ids[0],
                    text_message.message,
                    formatting_entities=text_message.entities
                )

        result = json.dumps({'message_ids': result_ids, 'bot_user_id': data['bot_user_id']})
        return f'/make_post {result}'

    async def publish_post_message_handler(self, data: dict):  # {'message_ids': [1, 2, 3], 'channel_id': 1, 'ad_id': 1}
        settings = await database_sync_to_async(models.Settings.objects.get)()

        messages = await self.client.get_messages(settings.archive_channel, ids=data['message_ids'])
        result = await self.client.send_message(data['channel_id'], messages[0].message, file=messages if messages[0].media else None)

        if isinstance(result, list):
            result_ids = [x.id for x in result]
        else:
            result_ids = [result.id]
        if messages[0].entities:
            with suppress(MessageNotModifiedError):
                await self.client.edit_message(
                    data['channel_id'],
                    result_ids[0],
                    messages[0].message,
                    formatting_entities=messages[0].entities
                )

        result = json.dumps({'message_ids': result_ids, 'ad_id': data['ad_id']})
        return f'/publish_post {result}'

    async def service_message_handler(self, event: Message | events.NewMessage.Event):
        logging.info(f'Service message for {self.userbot.fullname}: {event.message.message}')

        self.userbot.last_service_message = event.message.message
        self.userbot.last_service_message_date = datetime.now(timezone.utc)
        await database_sync_to_async(self.userbot.save)()
