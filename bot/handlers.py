import logging
from io import BytesIO
from datetime import datetime, timedelta, timezone
from asyncio import sleep, get_event_loop

from preferences import preferences

from telethon import TelegramClient, types
from telethon.types import ChannelParticipantsAdmins, InputPeerChannel, InputChannel
from telethon.tl.types.chatlists import ChatlistInvite
from telethon.tl.types.channels import ChannelParticipants
from telethon.tl.functions.channels import GetParticipantsRequest, EditAdminRequest, UpdateUsernameRequest
from telethon.tl.functions.chatlists import JoinChatlistInviteRequest, CheckChatlistInviteRequest

from app.settings import BASE_DIR, API_ID, API_HASH, USERBOT_PN_LIST
from bot import models, utils


class App:
    def __init__(self, phone_number: str, host: bool, func: int):
        name = phone_number
        if host:
            name = f'host{func}'
        self.n = USERBOT_PN_LIST.index(phone_number)
        self.client = TelegramClient(f'{BASE_DIR}/sessions/{name}', API_ID, API_HASH, receive_updates=False)
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
        for _ in await self.client.get_dialogs(): pass
        if not self.host or self.host and self.func == 0:
            await self.refresh_me()
        self.userbot = await models.UserBot.objects.aget(phone_number=self.phone_number)
        if self.host:
            if self.func == 0:
                await self.refresh()
                await self.loop_wrapper(self.check_post_deletions, preferences.Settings.check_post_deletions_interval)
            elif self.func == 1:
                await self.loop_wrapper(self.delete_old_posts, preferences.Settings.delete_old_posts_interval * 60)
        else:
            await self.join_channels()
            await self.loop_wrapper(self.check_post_views, preferences.Settings.check_post_views_interval)

    async def loop_wrapper(self, func, sleep_time, *args, **kwargs):
        await models.UserBot.objects.filter(user_id=self.user_id).aupdate(ping_time=datetime.now(timezone.utc))
        await utils.loop_wrapper(func, sleep_time, *args, **kwargs)

    async def refresh(self):
        async for user in models.UserBot.objects.all():
            if user.phone_number not in USERBOT_PN_LIST:
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
        new_username = utils.rand_username(channel.username)
        logging.info(f'Updating channel {channel.title} username to {new_username}')
        try:
            await self.client(UpdateUsernameRequest(channel.v2_id, new_username))
            channel.username = new_username
            channel.last_username_change = datetime.now(timezone.utc)
            await channel.asave()
            await models.Log.objects.acreate(type=models.types.Log.USERNAME_CHANGE, userbot=self.userbot, channel=channel)
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
            changed_that_day = await models.Log.objects.filter(
                channel=channel, type=models.types.Log.USERNAME_CHANGE, success=True,
                created__year=now.year, created__month=now.month, created__day=now.day,
            ).aexists()
            if not changed_that_day and \
                    channel.deletions_count_for_username_change and \
                    daily_deletions_count >= channel.deletions_count_for_username_change:
                if channel.last_username_change and \
                        channel.last_username_change > now - timedelta(minutes=preferences.Settings.username_change_cooldown):
                    continue
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
                            if post := await models.Post.objects.filter(limitation=limitation, post_id=message.id).afirst():
                                if (message.views - post.views) * 100 / post.views > limitation.views_difference_for_deletion:
                                    logging.info(f'Found views difference {limitation.views_difference_for_deletion}')
                                    if message.grouped_id and channel.delete_albums:
                                        if message.grouped_id not in grouped_messages:
                                            grouped_messages[message.grouped_id] = await utils.collect_media_group(self.client, message)
                                    else:
                                        single_messages.append(message)
                                    continue
                            else:
                                models.Post.objects.create(post_date=message.date, limitation=limitation, post_id=message.id, views=message.views)

            logging.info(f'Found {len(single_messages)} single messages and {len(grouped_messages)} grouped messages')
            for message in single_messages:
                await models.Log.objects.acreate(type=models.types.Log.DELETION, userbot=self.userbot, channel=channel, post_date=message.date, post_views=message.views)
                if channel.republish_today_posts and message.date.date() == now.date():
                    if channel.has_protected_content:
                        if message.media.photo:
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
                await models.Log.objects.acreate(type=models.types.Log.DELETION, userbot=self.userbot, channel=channel, post_date=grouped_message[0].date, post_views=grouped_message[0].views)
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


def main(number, host=False, func=None):
    utils.init_logger(number)
    app = App(number, host, func)
    get_event_loop().run_until_complete(app.start())
