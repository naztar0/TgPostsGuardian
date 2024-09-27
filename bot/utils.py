import json
import logging
import random
import string
from asyncio import sleep
from datetime import datetime, timedelta, timezone, date as date_t
from telethon import TelegramClient, types
from telethon.errors import FloodWaitError
from app.settings import MAX_SLEEP_TIME
from bot import models


async def loop_wrapper(func, sleep_time, *args, **kwargs):
    while True:
        try:
            await func(*args, **kwargs)
            await sleep(random.randint(sleep_time, sleep_time + 16))
        except FloodWaitError as e:
            logging.warning(f'Flood wait {e.seconds} seconds')
            await sleep(min(e.seconds, MAX_SLEEP_TIME))
        except (ValueError, BufferError) as e:
            logging.error(e)
            await sleep(60)
        except ConnectionError as e:
            logging.error(e)
            raise
        except Exception as e:
            logging.critical(e)
            await sleep(60 * 5)


async def is_username_change_unlocked(channel: models.Channel):
    now = datetime.now(timezone.utc)
    settings = await models.Settings.objects.aget()
    unlocked = (channel.last_username_change is None or
                channel.last_username_change < now - timedelta(minutes=settings.username_change_cooldown))
    return unlocked


async def collect_media_group(client: TelegramClient, post: types.Message):
    grouped_messages = []
    async for message in client.iter_messages(
        post.peer_id,
        reverse=True,
        limit=20,
        offset_id=post.id - 10
    ):
        if message.grouped_id == post.grouped_id:
            grouped_messages.append(message)
    return grouped_messages


def get_media_file_id(message: types.Message):
    available_media = ("audio", "document", "photo", "sticker", "animation", "video", "voice", "video_note",)
    if isinstance(message, types.Message):
        for kind in available_media:
            media = getattr(message, kind, None)

            if media is not None:
                break
        else:
            return None
    else:
        media = message
    return media.file_id


class LanguageStats:
    def __init__(self):
        self.today = datetime.now(timezone.utc).date()
        self.restrictions: dict[str, int] = {}  # {'English': 1000, 'Russian': -5} (minus means percentage)
        self.data: dict[date_t: dict[str, int]] = {}  # {'2021-01-21': {'English': 1000, 'Russian': 500}}

    def get_languages_graph_views(self, graphs, days=7):
        data = json.loads(graphs[0].json.data)
        now = datetime.now(timezone.utc)
        for x in range(days):
            date = now - timedelta(days=days - 1 - x)
            for y in data['columns'][1:]:
                curr = y[-days + x]
                if date.date() not in self.data:
                    self.data[date.date()] = {}
                self.data[date.date()][data['names'][y[0]]] = curr

    def parse_lang_stats_restrictions(self, restrictions: str):
        for restriction in restrictions.split('\n'):
            split = restriction.split()
            if len(split) != 2:
                continue
            lang, value = split
            if value[-1] == '%':
                value = '-' + value[:-1]
            self.restrictions[lang.capitalize()] = int(value)

    def get_data(self, date: date_t = None):
        if date is None:
            date = self.today
        return self.data[date]

    def get_total(self, date: date_t = None):
        if date is None:
            date = self.today
        return sum(self.data[date].values())
    
    def get_others(self, date: date_t = None):
        if date is None:
            date = self.today
        return sum(value for lang, value in self.data[date].items() if lang not in self.restrictions)


async def rand_username(username):
    sl = (await models.Settings.objects.aget()).username_suffix_length or 1
    base = username[:-sl]
    while True:
        new_username = base + ''.join(random.choices(string.digits, k=sl))
        if new_username != username:
            return new_username


def init_logger(number):
    formatter = logging.Formatter(f'%(levelname)s:{number}:%(name)s:%(message)s')
    logger = logging.getLogger()
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    return logger


def day_start(date: datetime = None):
    if date is None:
        date = datetime.now(timezone.utc)
    return datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
