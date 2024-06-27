import os
import logging
from time import sleep
from django.core.management.base import BaseCommand
from telethon import errors
from app.settings import BASE_DIR, USERBOT_PN_LIST, USERBOT_HOST_LIST, HOST_FUNC_COUNT
from bot import handlers, login
# noinspection PyUnresolvedReferences
import sqlite3


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('phone_number', nargs='?', type=str)
        parser.add_argument('--init', action='store_true')
        parser.add_argument('--host', nargs='?', type=int)
        parser.add_argument('--func', nargs='?', type=int)

    def handle(self, *args, **options):
        if options['init']:
            logging.info('Initializing')
            for i, phone_number in enumerate(USERBOT_HOST_LIST, 1):
                print(i, phone_number)
                login.main(phone_number, i)
            for i, phone_number in enumerate(USERBOT_PN_LIST):
                print(i, phone_number)
                login.main(phone_number)
            return
        if phone_number := options['phone_number']:
            logging.info(f'Starting {phone_number}')
            pid = os.getpid()
            if options['host'] is None:
                with open(f'{BASE_DIR}/pids/{phone_number}.pid', 'w') as f:
                    f.write(str(pid))
                try:
                    handlers.main(phone_number)
                except (errors.BadRequestError, errors.UnauthorizedError) as e:
                    logging.error(f'{phone_number} {e}')
                return
            if options['func'] is not None:
                with open(f'{BASE_DIR}/pids/{phone_number}-host-{options["host"]}-func-{options["func"]}.pid', 'w') as f:
                    f.write(str(pid))
                try:
                    handlers.main(phone_number, options['host'], options['func'])
                except (errors.BadRequestError, errors.UnauthorizedError) as e:
                    logging.error(f'{phone_number} {e}')
            else:
                for i in range(1, HOST_FUNC_COUNT + 1):
                    logging.info(f'Starting {phone_number} host-{options["host"]} func-{i}')
                    if os.name == 'posix':
                        os.system(f'cd {BASE_DIR} && nohup venv/bin/python manage.py start {phone_number} --host {options["host"]} --func {i} &')
                    elif os.name == 'nt':
                        os.system(f'cd {BASE_DIR} && start /B venv/Scripts/python.exe manage.py start {phone_number} --host {options["host"]} --func {i}')
                    sleep(1)
            return
        if os.name == 'posix':
            for i, phone_number in enumerate(USERBOT_HOST_LIST, 1):
                os.system(f'cd {BASE_DIR} && nohup venv/bin/python manage.py start {phone_number} --host {i} &')
                sleep(5)
            for phone_number in USERBOT_PN_LIST:
                os.system(f'cd {BASE_DIR} && nohup venv/bin/python manage.py start {phone_number} &')
                sleep(1)
        elif os.name == 'nt':
            for i, phone_number in enumerate(USERBOT_HOST_LIST, 1):
                os.system(f'cd {BASE_DIR} && start /B venv/Scripts/python.exe manage.py start {phone_number} --host {i}')
                sleep(5)
            for phone_number in USERBOT_PN_LIST:
                os.system(f'cd {BASE_DIR} && start /B venv/Scripts/python.exe manage.py start {phone_number}')
                sleep(1)
