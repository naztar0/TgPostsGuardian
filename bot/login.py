# noinspection PyUnresolvedReferences
import sqlite3

from pyrogram import Client

from app.settings import BASE_DIR, API_ID, API_HASH, HOST_FUNC_COUNT


def main(number, host=False):
    if host:
        for i in range(HOST_FUNC_COUNT):
            client = Client(f'host{i}', API_ID, API_HASH, phone_number=number,  workdir=f'{BASE_DIR}/sessions', device_model='PC', app_version='1.0.0')
            client.start()
    else:
        client = Client(number, API_ID, API_HASH, phone_number=number,  workdir=f'{BASE_DIR}/sessions', device_model='PC', app_version='1.0.0')
        client.start()
