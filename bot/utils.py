import json
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pyrogram import types
from pyrogram.errors import FloodWait

base_dir = Path(__file__).parent
temp_dir = base_dir / 'temp'


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
