from django.contrib import admin
from django.contrib.auth.models import User as DjangoUser, Group as DjangoGroup
from django.utils.translation import gettext_lazy as _

from bot import models
from .channel import ChannelAdmin
from .limitation import LimitationAdmin
from .log import LogAdmin
from .post_check import PostCheckAdmin
from .settings import SettingsAdmin
from .stats_views import StatsViewsAdmin
from .userbot import UserBotAdmin


admin.site.site_header = admin.site.site_title = _('admin_panel')
admin.site.site_url = ''

admin.site.unregister(DjangoUser)
admin.site.unregister(DjangoGroup)
admin.site.enable_nav_sidebar = False


admin.site.register(models.Channel, ChannelAdmin)
admin.site.register(models.Limitation, LimitationAdmin)
admin.site.register(models.Log, LogAdmin)
admin.site.register(models.PostCheck, PostCheckAdmin)
admin.site.register(models.Settings, SettingsAdmin)
admin.site.register(models.StatsViews, StatsViewsAdmin)
admin.site.register(models.UserBot, UserBotAdmin)
