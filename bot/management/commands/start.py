import os
import logging
from time import sleep
from django.core.management.base import BaseCommand
from telethon import errors
from app.settings import BASE_DIR, USERBOT_PN_LIST, DEBUG, HOST_FUNC_COUNT
from bot import handlers, login
# noinspection PyUnresolvedReferences
import sqlite3


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('phone_number', nargs='?', type=str)
        parser.add_argument('--init', action='store_true')
        parser.add_argument('--host', action='store_true')
        parser.add_argument('--func', nargs='?', type=int)

    def handle(self, *args, **options):
        if options['init']:
            logging.info('Initializing')
            for i, phone_number in enumerate(USERBOT_PN_LIST):
                print(i, phone_number)
                login.main(phone_number, i == 0)
            return
        if phone_number := options['phone_number']:
            logging.info(f'Starting {phone_number}')
            pid = os.getpid()
            if not options['host']:
                with open(f'{BASE_DIR}/pids/{phone_number}.pid', 'w') as f:
                    f.write(str(pid))
                try:
                    handlers.main(phone_number)
                except (errors.BadRequestError, errors.UnauthorizedError) as e:
                    logging.error(f'{phone_number} {e}')
                return
            if options['func'] is not None:
                with open(f'{BASE_DIR}/pids/host{options["func"]}.pid', 'w') as f:
                    f.write(str(pid))
                try:
                    handlers.main(phone_number, options['host'], options['func'])
                except (errors.BadRequestError, errors.UnauthorizedError) as e:
                    logging.error(f'{phone_number} {e}')
            else:
                for i in range(HOST_FUNC_COUNT):
                    if os.name == 'posix':
                        os.system(f'cd {BASE_DIR} && nohup venv/bin/python manage.py start {phone_number} --host --func {i} &')
                    elif os.name == 'nt':
                        os.system(f'cd {BASE_DIR} && start /B venv/Scripts/python.exe manage.py start {phone_number} --host --func {i}')
                    if i == 0:
                        sleep(1)
            return
        if os.name == 'posix':
            for i, phone_number in enumerate(USERBOT_PN_LIST):
                os.system(f'cd {BASE_DIR} && nohup venv/bin/python manage.py start {phone_number} {"--host" if i == 0 else ""} &')
                if i == 0:
                    sleep(5)
                else:
                    sleep(1)
        elif os.name == 'nt':
            for i, phone_number in enumerate(USERBOT_PN_LIST):
                if DEBUG:
                    os.system(f'cd {BASE_DIR} && .\\venv\\Scripts\\python.exe manage.py start {phone_number} {"--host" if i == 0 else ""}')
                else:
                    os.system(f'cd {BASE_DIR} && start /B venv/Scripts/python.exe manage.py start {phone_number} {"--host" if i == 0 else ""}')
                if i == 0:
                    sleep(5)
                else:
                    sleep(1)
