from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from bot.utils import admin_format_dt


class UserBotSessionAdmin(admin.ModelAdmin):
    list_display = ['created', 'userbot_custom', 'channels_custom', 'mode', 'ping_time_custom']
    search_fields = ['userbot__phone_number', 'userbot__username', 'userbot__first_name', 'userbot__user_id']
    list_filter = ['userbot', 'mode', 'channels']
    date_hierarchy = 'created'
    list_per_page = 50

    fieldsets = [
        (_('parameters'), {'fields': ['userbot', 'channels', 'mode', 'ping_time', 'authorization']}),
    ]

    def userbot_custom(self, obj):
        if not obj.userbot:
            return '-'
        return format_html('<a href="{url}">{userbot}</a>',
                           url=reverse('admin:bot_userbot_change', args=[obj.userbot.user_id]),
                           userbot=obj.userbot)
    userbot_custom.short_description = _('userbot')

    def channels_custom(self, obj):
        items = format_html_join(
            '',
            '<li><a href="{}">{}</a></li>',
            ((reverse('admin:bot_channel_change', args=[x.channel_id]), x.title)
             for x in obj.channels.all())
        )
        if not items:
            return '-'
        return format_html('<ol class="compact">{items}</ol>', items=items)
    channels_custom.short_description = _('channels')

    def ping_time_custom(self, obj):
        if not obj.ping_time:
            return '-'
        return admin_format_dt(obj.ping_time)
    ping_time_custom.short_description = _('ping_time_utc')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
