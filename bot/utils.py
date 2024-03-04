import json
import logging
import random
import string
from asyncio import sleep
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, types
from telethon.errors import FloodWaitError
from preferences import preferences


async def loop_wrapper(func, sleep_time, *args, **kwargs):
    while True:
        try:
            await func(*args, **kwargs)
            await sleep(random.randint(sleep_time, sleep_time + 16))
        except FloodWaitError as e:
            logging.warning(f'Flood wait {e.seconds} seconds')
            await sleep(e.seconds)
        except ValueError as e:
            logging.error(e)
            await sleep(60)


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


def get_languages_graph_views(graphs, exceptions, days=7):
    now = datetime.now(timezone.utc)
    data = json.loads(graphs[0].json.data)
    total_views_list = []
    for x in range(days):
        date = now - timedelta(days=days - 1 - x)
        total = 0
        restricted = 0
        for y in data['columns']:
            curr = y[-days + x]
            total += curr
            if data['names'][y[0]] not in exceptions:
                restricted += curr
        total_views_list.append((str(date.date()), total, restricted))
    return total_views_list


def rand_username(username):
    sl = preferences.Settings.username_suffix_length or 1
    base = username[:-sl]
    while True:
        new_username = base + ''.join(random.choices(string.digits, k=sl))
        if new_username != username:
            return new_username
