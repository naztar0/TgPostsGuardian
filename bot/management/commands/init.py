import logging
import asyncio
import os
from django.core.management.base import BaseCommand
from app.settings import USERBOT_PN_LIST, USERBOT_HOST_LIST, SESSIONS_DIR
from bot import login, models


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--skip-codes', action='store_true')
        parser.add_argument('--remove-skipped', action='store_true')

    def handle(self, *args, **options):
        logging.info('Initializing')
        for file in os.listdir(SESSIONS_DIR):
            if file.endswith('-journal'):
                logging.warning(f'Removing journal {file}')
                os.remove(SESSIONS_DIR / file)
        for user in models.UserBot.objects.all():
            if user.phone_number not in USERBOT_HOST_LIST and user.phone_number not in USERBOT_PN_LIST:
                logging.warning(f'Removing old userbot {user.phone_number}')
                user.delete()
        for i, phone_number in enumerate(USERBOT_PN_LIST):
            logging.info(i, phone_number)
            try:
                asyncio.run(login.initialize(phone_number, False, options['skip_codes'], options['remove_skipped']))
            except login.SkipCode:
                logging.warning('Code skipped')
        for i, phone_number in enumerate(USERBOT_HOST_LIST):
            logging.info(i, phone_number)
            try:
                asyncio.run(login.initialize(phone_number, True, options['skip_codes'], options['remove_skipped']))
            except login.SkipCode:
                logging.warning('Code skipped')
