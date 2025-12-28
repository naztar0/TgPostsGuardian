import json
import logging
import os
import random
from typing import Coroutine, Any
from asyncio import sleep, gather, create_task
from datetime import datetime, timedelta, timezone, date as date_t
from django.utils import dateformat
from telethon import TelegramClient, types
from telethon.errors import FloodWaitError
from app.settings import MAX_SLEEP_TIME
from bot import models
from bot.types import UsernameChangeReason


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
            raise


async def gather_coroutines(coroutines: list[Coroutine[Any, Any, Any]]):
    tasks = []
    try:
        tasks = [create_task(coro) for coro in coroutines]
        await gather(*tasks)
    except ConnectionError:
        for task in tasks:
            task.cancel()
        raise


async def is_username_change_unlocked(channel: models.Channel):
    now = datetime.now(timezone.utc)
    settings = await models.Settings.objects.aget()
    unlocked = (channel.last_username_change is None or
                channel.last_username_change < now - timedelta(minutes=settings.username_change_cooldown))
    return unlocked


async def collect_media_group(client: TelegramClient, post: types.Message):
    grouped_messages: list[types.Message] = []
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


def _get_graph_name(name: str):
    if not name or not isinstance(name, str):
        return name
    return name.replace(' ', '_').lower()


class StatsHandler:
    def __init__(self):
        self.today = datetime.now(timezone.utc).date()
        self.restrictions: dict[str, int] = {}  # {'English': 1000, 'Russian': -5} (minus means percentage)
        self.data: dict[date_t, dict[str, int]] = {}  # {'2021-01-21': {'English': 1000, 'Russian': 500}}

    def get_graph_views(self, graph, days=7):
        data = json.loads(graph.json.data)
        now = datetime.now(timezone.utc)
        for x in range(days):
            date = now - timedelta(days=days - 1 - x)
            for y in data['columns'][1:]:
                curr = y[-days + x]
                if date.date() not in self.data:
                    self.data[date.date()] = {}
                self.data[date.date()][_get_graph_name(data['names'][y[0]])] = curr

    def parse_stats_restrictions(self, restrictions: str):
        for restriction in restrictions.split('\n'):
            split = restriction.split()
            if len(split) != 2:
                continue
            key, value = split
            if value[-1] == '%':
                value = '-' + value[:-1]
            self.restrictions[key.lower()] = int(value)

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
        return sum(value for key, value in self.data[date].items() if key not in self.restrictions)


class MessageData:
    def __init__(
            self,
            limitation: models.Limitation,
            message: types.Message = None,
            media_group: list[types.Message] = None
    ):
        self.limitation = limitation
        self.message = message
        self.media_group = media_group


def rand_username(username: str, suffix_len: int):
    base = username[:-suffix_len]

    # generate a number with zero-padding (e.g., 004, 129, 873)
    num = random.randrange(10**suffix_len)
    new_username = f'{base}{num:0{suffix_len}d}'

    if new_username == username:
        num = (num + 1) % (10**suffix_len)
        new_username = f'{base}{num:0{suffix_len}d}'

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


def remove_file(filename):
    os.remove(filename)


def is_limitation_highest(limitation: models.Limitation, limitations: list[models.Limitation], date: date_t = None):
    if not date:
        date = datetime.now(timezone.utc).date()

    for lim in limitations:
        if (
                lim.type == limitation.type and
                lim.start <= date <= lim.end and lim.priority < limitation.priority and
                bool(lim.views) == bool(limitation.views) and
                bool(lim.views_difference) == bool(limitation.views_difference)
        ):
            logging.info(
                f'Skipping limitation {limitation.title} ({limitation.start} - {limitation.end}) with priority {limitation.priority} '
                f'because it is inside {lim.title} ({lim.start} - {lim.end}) with priority {lim.priority}')
            return False

    return True


def is_limitation_activated(
        limitation: models.Limitation,
        limitations: list[models.Limitation],
        logged_ids: set[int],
        checked: set[int] = None
):
    if checked is None:
        checked = set()
    next_checked = checked | {limitation.id}

    if not limitation.start_after_limitation and not limitation.end_after_limitation:
        return True

    start, end = None, None

    for lim in limitations:
        if limitation.start_after_limitation_id == lim.id:
            start = lim
        if limitation.end_after_limitation_id == lim.id:
            end = lim

    if start and start.id == limitation.id:
        logging.warning(f'Limitation {limitation.title} has itself as "Start trigger", activation is impossible')
        return False
    if start and start.id in checked:
        logging.warning(f'Circular dependency in limitation {start.title}, activation is impossible')
        return False
    if end and end.id in checked:
        logging.warning(f'Circular dependency in limitation {end.title}, activation is impossible')
        return False

    if start and not is_limitation_activated(start, limitations, logged_ids, next_checked):
        logging.info(f'Limitation {limitation.title} is not activated because {start.title} is not activated')
        return False
    if end and end.id != limitation.id and is_limitation_activated(end, limitations, logged_ids, next_checked):
        logging.info(f'Limitation {limitation.title} is not activated because {end.title} is activated')
        return False

    if start and start.id not in logged_ids:
        logging.info(f'Limitation {limitation.title} is not activated because {start.title} is not logged')
        return False
    if end and end.id in logged_ids:
        logging.info(f'Limitation {limitation.title} is not activated because {end.title} is logged')
        return False

    return True


async def send_username_change_request(
        client: TelegramClient,
        channel: models.Channel,
        limitation: models.Limitation,
        reason: UsernameChangeReason,
        comment: str = None
):
    request = {
        'action': 'update_username',
        'channel_id': channel.v2_id,
        'limitation_id': limitation.id,
        'reason': reason,
        'comment': comment
    }
    msg = f'ACTION {json.dumps(request)}'
    await client.send_message(channel.owner.user_id, msg)


def admin_format_dt(dt: datetime):
    return dateformat.format(dt, 'j M Y G:i')
