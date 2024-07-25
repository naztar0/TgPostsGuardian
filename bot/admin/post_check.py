from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class PostCheckAdmin(admin.ModelAdmin):
    list_display = ['post_date', 'channel_custom', 'post_id', 'views']
    list_display_links = None
    list_per_page = 25

    search_fields = ['post_id', 'channel__title']
    list_filter = ['channel__title']

    def channel_custom(self, obj):
        if obj.channel:
            return format_html(f'<a href="/bot/channel/{obj.channel.channel_id}">{obj.channel.title}</a>')
        else:
            return '-'
    channel_custom.short_description = _('channel')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
