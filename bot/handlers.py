import logging
import random
import string
import time
from datetime import datetime, timedelta, timezone
# noinspection PyUnresolvedReferences
import sqlite3

from preferences import preferences

from pyrogram import Client
from pyrogram import types
from pyrogram.raw.types.chatlists import ChatlistInvite
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.chatlists import JoinChatlistInvite, CheckChatlistInvite

from app.settings import BASE_DIR, API_ID, API_HASH, USERBOT_PN_LIST
from bot import models, utils


def loop_wrapper(func, sleep_time, *args, **kwargs):
    while True:
        try:
            func(*args, **kwargs)
            time.sleep(random.randint(sleep_time, sleep_time + 16))
        except FloodWait as e:
            logging.warning(f'Flood wait {e.value} seconds')
            time.sleep(e.value)
        except Exception as e:
            logging.error(e)
            time.sleep(60)


# noinspection PyTypeChecker
class App:
    def __init__(self, phone_number: str, host: bool, func: int):
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
        if self.host:
            if self.func == 0:
                self.refresh_me()
                self.refresh()
                self.check_post_deletions()
            elif self.func == 1:
                self.delete_old_posts()
            return
        self.refresh_me()
        time.sleep(5)  # wait for other bots to refresh themselves
        self.userbot = models.UserBot.objects.get(phone_number=self.phone_number)
        self.join_channels()
        loop_wrapper(self.check_post_views, 10, self)

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

    def refresh_me(self):
        me: types.User = self.client.get_me()
        models.UserBot.objects.update_or_create(user_id=me.id, defaults={
            'username': me.username,
            'first_name': me.first_name,
            'last_name': me.last_name,
            'phone_number': me.phone_number
        })

    def join_channels(self):
        check: ChatlistInvite = self.client.invoke(CheckChatlistInvite(slug=preferences.Settings.chatlist_invite))
        channels = [channel for channel in check.chats if channel.left]
        if channels:
            self.client.invoke(JoinChatlistInvite(slug=preferences.Settings.chatlist_invite, peers=channels))
            logging.info(f'Joined {len(channels)} channels: {", ".join([channel.title for channel in channels])}')

    def change_username(self, channel: models.Channel):
        username = channel.username[:-preferences.Settings.username_suffix_length]
        new_username = username + ''.join(random.choices(string.digits, k=preferences.Settings.username_suffix_length))
        logging.info(f'Updating channel {channel.title} username to {new_username}')
        try:
            self.client.set_chat_username(channel.id, new_username)
        except Exception as e:
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
            daily_deletions_count = models.Log.objects.filter(channel=channel, type=models.types.Log.DELETION,
                                                              created__year=now.year, created__month=now.month, created__day=now.day).count()
            if daily_deletions_count >= channel.deletions_count_for_username_change and channel.change_username:
                if models.Log.objects.filter(channel=channel, type=models.types.Log.USERNAME_CHANGE,
                                             created__year=now.year, created__month=now.month, created__day=now.day).exists():
                    continue
                self.change_username(channel)
                models.Log.objects.create(type=models.types.Log.USERNAME_CHANGE, userbot=self.userbot, channel=channel)

    def delete_old_posts(self):
        now = datetime.now(timezone.utc)
        for channel in models.Channel.objects.all():
            logging.info(f'Checking channel {channel.title}')
            messages = []
            for message in self.client.get_chat_history(
                    channel.v2_id, limit=100,
                    offset_date=now - timedelta(days=preferences.Settings.delete_posts_after_days)
            ):
                messages.append(message.id)
            logging.info(f'Found {len(messages)} messages')
            self.client.delete_messages(channel.v2_id, messages)
            time.sleep(5)

    def check_post_views(self):
        now = datetime.now(timezone.utc)
        end_date = now.date() - timedelta(days=4)
        for channel in self.get_channels():
            logging.info(f'Checking channel {channel.channel_id}')
            single_messages: list[types.Message] = []
            grouped_messages: dict[str, list[types.Message]] = {}
            for message in self.client.get_chat_history(channel.v2_id):
                if message.date.date() < end_date:
                    break
                if not message.views:
                    continue
                if message.date < now - timedelta(days=channel.track_posts_after_days):
                    if post := models.Post.objects.filter(channel=channel, post_id=message.id).first():
                        if message.views * 100 / post.views > channel.views_difference_for_deletion:
                            if message.media_group_id and channel.delete_albums:
                                if message.media_group_id not in grouped_messages:
                                    grouped_messages[message.media_group_id] = message.get_media_group()
                            else:
                                single_messages.append(message)
                            continue
                    else:
                        models.Post.objects.create(post_date=message.date, channel=channel, post_id=message.id, views=message.views)
                if message.text:
                    logging.info(f'Found message {message.text[:20]}')
                logging.info(f'Found views {message.views}')
                for limitation in models.Limitation.objects.filter(channel=channel):
                    if limitation.no_start_date:
                        limitation.start_date = datetime(1970, 1, 1).date()
                    if limitation.no_end_date:
                        limitation.end_date = now.date()
                    if limitation.start_date <= message.date.date() <= limitation.end_date and message.views > limitation.views:
                        if message.media_group_id and channel.delete_albums:
                            if message.media_group_id not in grouped_messages:
                                grouped_messages[message.media_group_id] = message.get_media_group()
                        else:
                            single_messages.append(message)
            logging.info(f'Found {len(single_messages)} single messages and {len(grouped_messages)} grouped messages')
            for message in single_messages:
                models.Log.objects.create(type=models.types.Log.DELETION, userbot=self.userbot, channel=channel, post_date=message.date)
                if channel.republish_today_posts and message.date.date() == now.date():
                    if channel.has_protected_content:
                        if file_id := utils.get_media_file_id(message):
                            self.client.send_cached_media(channel.v2_id, file_id, message.text)
                        else:
                            self.client.send_message(channel.v2_id, message.text)
                    else:
                        self.client.copy_message(channel.v2_id, channel.v2_id, message.id)
                time.sleep(1)
            self.client.delete_messages(channel.v2_id, [message.id for message in single_messages])
            time.sleep(1)
            for grouped_message in grouped_messages.values():
                models.Log.objects.create(type=models.types.Log.DELETION, userbot=self.userbot, channel=channel, post_date=grouped_message[0].date)
                if channel.republish_today_posts and grouped_message[0].date.date() == now.date():
                    # send only first media from group
                    if channel.has_protected_content:
                        caption = list(filter(lambda x: x.text, grouped_message))
                        caption = caption[0].message if caption else ''
                        self.client.send_cached_media(channel.v2_id, utils.get_media_file_id(grouped_message[0]), caption)
                    else:
                        self.client.copy_media_group(channel.v2_id, channel.v2_id, grouped_message[0].id)
                time.sleep(1)
                self.client.delete_messages(channel.v2_id, [message.id for message in grouped_message])
                time.sleep(1)


def main(number, host=False, func=None):
    app = App(number, host, func)
    app.start()
