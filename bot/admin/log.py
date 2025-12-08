from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class LogAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_custom', 'type', 'channel_custom', 'post_date', 'post_views', 'success', 'reason']
    list_per_page = 25

    date_hierarchy = 'created'
    search_fields = ['userbot__first_name', 'userbot__last_name', 'channel__channel_title']
    list_filter = ['type', 'success', 'channel__title', 'reason']

    fieldsets = [
        (_('parameters'), {'fields': ['userbot', 'type', 'channel', 'post_id', 'post_date', 'post_views', 'reason',
                                      'success', 'comment', 'error_message']}),
    ]

    def user_custom(self, obj):
        if obj.userbot:
            full_name = f'{obj.userbot.first_name}&nbsp;{obj.userbot.last_name}' \
                if obj.userbot.last_name \
                else obj.userbot.first_name
            return format_html('<a href="/bot/userbot/?q={user_id}">{full_name}</a>',
                               user_id=obj.userbot.user_id, full_name=full_name)
        else:
            return '-'
    user_custom.short_description = _('userbot')

    def channel_custom(self, obj):
        if obj.channel:
            return format_html('<a href="/bot/channel/?q={channel_id}">{title}</a>',
                               channel_id=obj.channel.channel_id, title=obj.channel.title)
        else:
            return '-'
    channel_custom.short_description = _('channel')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
