from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BotConfig(AppConfig):
    name = 'bot'
    verbose_name = _('bot')
