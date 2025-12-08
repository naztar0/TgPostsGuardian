import os
import logging
from django.core.management.base import BaseCommand
from telethon import errors
from bot import handlers

phone_number = os.environ['PHONE_NUMBER']
HOST = os.environ['HOST'] == '1'
FUNC = int(os.environ['FUNC'])


class Command(BaseCommand):
    def handle(self, *args, **options):
        logging.info(f'Starting {phone_number}')
        try:
            handlers.main(phone_number, HOST, FUNC)
        except (errors.BadRequestError, errors.UnauthorizedError) as e:
            logging.error(f'{phone_number} {e}')
