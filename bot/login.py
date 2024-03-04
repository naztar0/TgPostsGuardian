# noinspection PyUnresolvedReferences
import sqlite3

from telethon import TelegramClient

from app.settings import BASE_DIR, API_ID, API_HASH, HOST_FUNC_COUNT


def main(number, host=False):
    if host:
        for i in range(HOST_FUNC_COUNT):
            client = TelegramClient(f'{BASE_DIR}/sessions/host{i}', API_ID, API_HASH, receive_updates=False)
            client.start(lambda: number)
    else:
        client = TelegramClient(f'{BASE_DIR}/sessions/{number}', API_ID, API_HASH, receive_updates=False)
        client.start(lambda: number)
