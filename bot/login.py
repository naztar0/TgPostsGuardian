# noinspection PyUnresolvedReferences
import sqlite3
import logging
import asyncio
import os

from telethon import TelegramClient, events

from app.settings import BASE_DIR, API_ID, API_HASH, HOST_FUNC_COUNT, USERBOT_HOST_LIST
from bot.handlers.app import App


def initialize(number, host: int = 0):
    loop = asyncio.get_event_loop()
    if host:
        for i in range(1, HOST_FUNC_COUNT + 1):
            app = App(number, host, i)
            app.client.start(lambda: number)
            if i == 1:
                loop.run_until_complete(app.join_channels())
                if host == len(USERBOT_HOST_LIST):
                    loop.run_until_complete(app.refresh())
    else:
        app = App(number, host)
        app.client.start(lambda: number)
        loop.run_until_complete(app.join_channels())


def listen_codes(numbers: list[str]):
    async def callback(event: events.NewMessage.Event):
        print(event.message.message)

    clients = []
    for number in numbers:
        for file in os.listdir(f'{BASE_DIR}/sessions'):
            if file.startswith(number):
                logging.info(f'Initializing session for {number}, file: {file}')
                clients.append(TelegramClient(f'{BASE_DIR}/sessions/{file}', API_ID, API_HASH))
                clients[-1].start(lambda: number)
                break
        else:
            logging.error(f'No session file for {number}')

        for i in range(len(clients)):
            clients[i].add_event_handler(callback, events.NewMessage(777000, func=lambda e: e.message.message, incoming=True))
    logging.info('Listening codes...')

    loop = asyncio.get_event_loop()
    loop.run_forever()
