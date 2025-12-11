from django.core.management.base import BaseCommand
from app.settings import USERBOT_PN_LIST, USERBOT_HOST_LIST
from bot import login


class Command(BaseCommand):
    def handle(self, *args, **options):
        login.listen_codes(USERBOT_PN_LIST + USERBOT_HOST_LIST)
