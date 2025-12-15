import logging
import asyncio
import os
from telethon import TelegramClient, events
from app.settings import SESSIONS_DIR, API_ID, API_HASH, HOST_FUNC_COUNT
from bot.handlers.app import App


class SkipCode(Exception): pass
def skip_code_callback(): raise SkipCode()


async def initialize(number, host: bool, skip_code: bool, remove_skipped: bool):
    code_callback = skip_code_callback if skip_code else None
    if host:
        for i in range(1, HOST_FUNC_COUNT + 1):
            app = App(number, host, i)
            try:
                await app.client.start(lambda: number, code_callback=code_callback)
            except SkipCode:
                if remove_skipped:
                    app.remove_session()
                if i == HOST_FUNC_COUNT:
                    raise
    else:
        app = App(number, host)
        try:
            await app.client.start(lambda: number, code_callback=code_callback)
        except SkipCode:
            if remove_skipped:
                app.remove_session()


def listen_codes(numbers: list[str]):
    async def callback(event: events.NewMessage.Event):
        print(event.message.message)

    clients = []
    for number in numbers:
        for file in os.listdir(SESSIONS_DIR):
            if file.startswith(number):
                logging.warning(f'Initializing session for {number}, file: {file}')
                clients.append(TelegramClient(SESSIONS_DIR / file, API_ID, API_HASH))
                clients[-1].start(lambda: number)
                break
        else:
            logging.error(f'No session file for {number}')

    for i in range(len(clients)):
        clients[i].add_event_handler(callback, events.NewMessage(777000, func=lambda e: e.message.message, incoming=True))
    logging.warning('Listening codes...')

    loop = asyncio.get_event_loop()
    loop.run_forever()
