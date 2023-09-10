import logging
import time
from io import BytesIO
from datetime import datetime, timedelta, timezone

from preferences import preferences

from pyrogram import Client
from pyrogram import types
from pyrogram.raw.types import ChannelParticipantsAdmins
from pyrogram.raw.types.chatlists import ChatlistInvite
from pyrogram.raw.base.channels import ChannelParticipants
from pyrogram.raw.functions.channels import GetParticipants
from pyrogram.raw.functions.chatlists import JoinChatlistInvite, CheckChatlistInvite

from app.settings import BASE_DIR, API_ID, API_HASH, USERBOT_PN_LIST
from bot import models, utils
from bot.base import BaseApp


# noinspection PyTypeChecker
class App(BaseApp):
    def __init__(self, phone_number: str, host: bool, func: int):
        super().__init__()
        name = phone_number
        if host:
            name = f'host{func}'
        self.n = USERBOT_PN_LIST.index(phone_number)
        self.client = Client(name, API_ID, API_HASH, phone_number=phone_number, workdir=f'{BASE_DIR}/sessions', device_model='PC', app_version='1.0.0')
        self.phone_number = phone_number
        self.host = host
        self.userbot = None
        self.channels = []
        self.func = func

    def start(self):
        self.client.start()
        for _ in self.client.get_dialogs(): pass
        if not self.host or self.host and self.func == 0:
            self.refresh_me()
        self.userbot = models.UserBot.objects.get(phone_number=self.phone_number)
        if self.host:
            if self.func == 0:
                self.refresh()
                utils.loop_wrapper(self.check_post_deletions, preferences.Settings.check_post_deletions_interval)
            elif self.func == 1:
                utils.loop_wrapper(self.delete_old_posts, preferences.Settings.delete_old_posts_interval * 60)
        else:
            self.join_channels()
            utils.loop_wrapper(self.check_post_views, preferences.Settings.check_post_views_interval)

    def refresh(self):
        for user in models.UserBot.objects.all():
            if user.phone_number not in USERBOT_PN_LIST:
                user.delete()

        for channel in models.Channel.objects.all():
            channel_api: types.Chat = self.client.get_chat(channel.v2_id)
            channel.title = channel_api.title
            channel.username = channel_api.username
            channel.has_protected_content = channel_api.has_protected_content
            channel.save()

            cp: ChannelParticipants = self.client.invoke(
                GetParticipants(channel=self.client.resolve_peer(channel.v2_id), filter=ChannelParticipantsAdmins(), offset=0, limit=100, hash=0)
            )
            admins = [admin.user_id for admin in cp.participants]
            for user in models.UserBot.objects.all():
                if user.user_id not in admins:
                    privileges = types.ChatPrivileges(can_delete_messages=True, can_post_messages=True, can_edit_messages=True, can_change_info=True)
                    self.client.promote_chat_member(channel.v2_id, user.user_id, privileges)
                    logging.info(f'Promoted {user.user_id} to admin in {channel.title}')
                    time.sleep(1)

    def refresh_me(self):
        me: types.User = self.client.get_me()
        models.UserBot.objects.update_or_create(user_id=me.id, defaults={
            'username': me.username,
            'first_name': me.first_name,
            'last_name': me.last_name,
            'phone_number': self.phone_number,
        })

    def join_channels(self):
        check: ChatlistInvite = self.client.invoke(CheckChatlistInvite(slug=preferences.Settings.chatlist_invite))
        channels = [channel for channel in check.chats if channel.left]
        if channels:
            self.client.invoke(JoinChatlistInvite(slug=preferences.Settings.chatlist_invite, peers=channels))
            logging.info(f'Joined {len(channels)} channels: {", ".join([channel.title for channel in channels])}')

    def change_username(self, channel: models.Channel):
        new_username = utils.rand_username(channel.username)
        logging.info(f'Updating channel {channel.title} username to {new_username}')
        try:
            self.client.set_chat_username(channel.v2_id, new_username)
            channel.username = new_username
            channel.last_username_change = datetime.now(timezone.utc)
            channel.save()
            models.Log.objects.create(type=models.types.Log.USERNAME_CHANGE, userbot=self.userbot, channel=channel)
        except Exception as e:
            models.Log.objects.create(type=models.types.Log.USERNAME_CHANGE, userbot=self.userbot, channel=channel, success=False)
            logging.error(e)
            time.sleep(5)

    def get_channels(self):
        channels = models.Channel.objects.all()
        if preferences.Settings.individual_allocations:
            channels_count = channels.count()
            userbot_count = models.UserBot.objects.count()
            if userbot_count <= channels_count:
                return channels[self.n::userbot_count]
            else:
                return [channels[self.n % channels_count]]
        else:
            return channels

    def check_post_deletions(self):
        now = datetime.now(timezone.utc)
        for channel in models.Channel.objects.all():
            daily_deletions_count = models.Log.objects.filter(channel=channel, type=models.types.Log.DELETION, success=True,
                                                              created__year=now.year, created__month=now.month, created__day=now.day).count()
            logging.info(f'Checking channel {channel.title} with {daily_deletions_count} daily deletions')
            changed_that_day = models.Log.objects.filter(channel=channel, type=models.types.Log.USERNAME_CHANGE, success=True,
                                                         created__year=now.year, created__month=now.month, created__day=now.day).exists()
            if not changed_that_day and \
                    channel.deletions_count_for_username_change and \
                    daily_deletions_count >= channel.deletions_count_for_username_change:
                if channel.last_username_change and \
                        channel.last_username_change > now - timedelta(minutes=preferences.Settings.username_change_cooldown):
                    continue
                self.change_username(channel)

    def delete_old_posts(self):
        now = datetime.now(timezone.utc)
        for channel in models.Channel.objects.all():
            logging.info(f'Checking channel {channel.title}')
            messages = []
            for message in self.client.get_chat_history(
                    channel.v2_id, limit=100,
                    offset_date=now - timedelta(days=channel.delete_posts_after_days)
            ):
                messages.append(message.id)
            logging.info(f'Found {len(messages)} messages')
            self.client.delete_messages(channel.v2_id, messages)
            time.sleep(5)

    def check_post_views(self):
        now = datetime.now(timezone.utc)
        for channel in self.get_channels():
            logging.info(f'Checking channel {channel.channel_id}')
            single_messages: list[types.Message] = []
            grouped_messages: dict[str, list[types.Message]] = {}
            limitations = list(models.Limitation.objects.filter(channel=channel).order_by('-created'))
            for message in self.client.get_chat_history(channel.v2_id):
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
                            if message.media_group_id and channel.delete_albums:
                                if message.media_group_id not in grouped_messages:
                                    grouped_messages[message.media_group_id] = message.get_media_group()
                            else:
                                single_messages.append(message)
                        if limitation.views_difference_for_deletion:
                            logging.info(f'Checking views difference {limitation.views_difference_for_deletion}')
                            if post := models.Post.objects.filter(limitation=limitation, post_id=message.id).first():
                                if (message.views - post.views) * 100 / post.views > limitation.views_difference_for_deletion:
                                    logging.info(f'Found views difference {limitation.views_difference_for_deletion}')
                                    if message.media_group_id and channel.delete_albums:
                                        if message.media_group_id not in grouped_messages:
                                            grouped_messages[message.media_group_id] = message.get_media_group()
                                    else:
                                        single_messages.append(message)
                                    continue
                            else:
                                models.Post.objects.create(post_date=message.date, limitation=limitation, post_id=message.id, views=message.views)

            logging.info(f'Found {len(single_messages)} single messages and {len(grouped_messages)} grouped messages')
            for message in single_messages:
                models.Log.objects.create(type=models.types.Log.DELETION, userbot=self.userbot, channel=channel, post_date=message.date, post_views=message.views)
                if channel.republish_today_posts and message.date.date() == now.date():
                    if channel.has_protected_content:
                        if message.photo:
                            photo: BytesIO = message.download(in_memory=True)
                            self.client.send_photo(channel.v2_id, photo, message.caption)
                        elif message.text or message.caption:
                            self.client.send_message(channel.v2_id, message.text or message.caption)
                    else:
                        self.client.copy_message(channel.v2_id, channel.v2_id, message.id)
                    time.sleep(1)
                self.client.delete_messages(channel.v2_id, message.id)
                time.sleep(1)
            for grouped_message in grouped_messages.values():
                models.Log.objects.create(type=models.types.Log.DELETION, userbot=self.userbot, channel=channel, post_date=grouped_message[0].date, post_views=grouped_message[0].views)
                if channel.republish_today_posts and grouped_message[0].date.date() == now.date():
                    if channel.has_protected_content:
                        # send only first photo from group
                        photos: list[types.Message] = list(filter(lambda x: x.photo, grouped_message))
                        photo: BytesIO = photos[0].download(in_memory=True) if photos else None
                        caption = list(filter(lambda x: x.caption, grouped_message))
                        caption = caption[0].message if caption else ''
                        if photo:
                            self.client.send_photo(channel.v2_id, photo, caption)
                        elif caption:
                            self.client.send_message(channel.v2_id, caption)
                    else:
                        self.client.copy_media_group(channel.v2_id, channel.v2_id, grouped_message[0].id)
                time.sleep(1)
                self.client.delete_messages(channel.v2_id, [message.id for message in grouped_message])
                time.sleep(1)


def main(number, host=False, func=None):
    app = App(number, host, func)
    app.start()
