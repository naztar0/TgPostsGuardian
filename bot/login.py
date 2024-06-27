# noinspection PyUnresolvedReferences
import sqlite3

from telethon import TelegramClient

from app.settings import BASE_DIR, API_ID, API_HASH, HOST_FUNC_COUNT


def main(number, host: int = 0):
    if host:
        for i in range(1, HOST_FUNC_COUNT + 1):
            client = TelegramClient(f'{BASE_DIR}/sessions/{number}-host-{host}-func-{i}', API_ID, API_HASH, receive_updates=False)
            client.start(lambda: number)
    else:
        client = TelegramClient(f'{BASE_DIR}/sessions/{number}', API_ID, API_HASH, receive_updates=False)
        client.start(lambda: number)
