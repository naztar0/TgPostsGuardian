from django.contrib import admin
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import gettext_lazy as _


class UserBotAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_id', 'channels_custom', 'username_custom', 'first_name', 'last_name', 'phone_number', 'ping_time']
    search_fields = ['user_id', 'username', 'first_name', 'last_name']
    list_filter = ['channels']
    date_hierarchy = 'created'
    list_per_page = 25

    def username_custom(self, obj):
        if obj.username:
            return format_html('<a href="tg://resolve?domain={username}">@{username}</a>', username=obj.username)
        else:
            return '-'
    username_custom.short_description = _('@username')

    def channels_custom(self, obj):
        return format_html_join(
            mark_safe('<br>'),
            '<a href="/bot/channel/{channel_id}">{title}</a>',
            [{'channel_id': x.channel_id, 'title': x.title} for x in obj.channels.all()]
        ) or '-'
    channels_custom.short_description = _('channels')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
