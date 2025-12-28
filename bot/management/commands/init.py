import logging
import asyncio
from django.core.management.base import BaseCommand
from bot import login, models


async def handle(**options):
    logging.info('Initializing')

    userbot_configs = [x async for x in models.UserBotConfig.objects.all()]
    active_userbot_configs = [x for x in userbot_configs if x.is_active]
    numbers = [x.phone_number for x in userbot_configs]

    async for user in models.UserBot.objects.all():
        if user.phone_number not in numbers:
            logging.warning(f'Removing old userbot {user.phone_number}')
            await user.adelete()

    for i, userbot_config in enumerate(active_userbot_configs):
        logging.warning(f'[{i}]: {userbot_config.phone_number}')
        try:
            await login.init_instances(
                userbot_config,
                options['skip_codes'],
                options['remove_skipped']
            )
        except login.SkipCode:
            logging.warning('Code skipped')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--skip-codes', action='store_true')
        parser.add_argument('--remove-skipped', action='store_true')

    def handle(self, *args, **options):
        asyncio.run(handle(**options))
