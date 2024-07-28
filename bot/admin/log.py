from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class LogAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_custom', 'type', 'channel_custom', 'post_date', 'post_views', 'success', 'reason', 'dummy']
    list_per_page = 25

    date_hierarchy = 'created'
    search_fields = ['userbot__first_name', 'userbot__last_name', 'channel__channel_title']
    list_filter = ['type', 'success', 'dummy', 'channel__title', 'reason']

    fieldsets = [
        (_('parameters'), {'fields': ['userbot', 'type', 'channel', 'post_id', 'post_date',
                                      'post_views', 'reason', 'success', 'dummy', 'error_message']}),
    ]

    def user_custom(self, obj):
        if obj.userbot:
            return format_html(f'<a href="/bot/user/?q={obj.userbot.user_id}">{obj.userbot.first_name}&nbsp;{obj.userbot.last_name}</a>')
        else:
            return '-'
    user_custom.short_description = _('userbot')

    def channel_custom(self, obj):
        if obj.channel:
            return format_html(f'<a href="/bot/channel/?q={obj.channel.channel_id}">{obj.channel.title}</a>')
        else:
            return '-'
    channel_custom.short_description = _('channel')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
