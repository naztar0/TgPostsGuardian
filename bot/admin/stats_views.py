from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class StatsViewsAdmin(admin.ModelAdmin):
    list_display = ['created', 'channel_custom', 'language', 'value']
    list_per_page = 25

    date_hierarchy = 'created'
    search_fields = ['channel__title']
    list_filter = ['channel__title']

    fieldsets = [
        (_('parameters'), {'fields': ['channel']}),
    ]

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

    def has_delete_permission(self, request, obj=None):
        return False
