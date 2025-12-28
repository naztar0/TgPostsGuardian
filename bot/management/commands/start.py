import os
import logging
from django.core.management.base import BaseCommand
from telethon import errors
from bot import handlers

session_id = int(os.environ['SESSION_ID'])


class Command(BaseCommand):
    def handle(self, *args, **options):
        logging.info(f'Starting {session_id}')
        try:
            handlers.main(session_id)
        except (errors.BadRequestError, errors.UnauthorizedError) as e:
            logging.error(f'{session_id} {e}')
