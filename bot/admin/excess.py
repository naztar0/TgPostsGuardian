from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class ExcessAdmin(admin.ModelAdmin):
    list_display = ['created', 'channel_custom', 'type', 'value']
    list_per_page = 25

    date_hierarchy = 'created'
    search_fields = ['channel__title']
    list_filter = ['channel__title', 'type']

    fieldsets = [
        (_('parameters'), {'fields': ['created', 'channel', 'type', 'value']}),
    ]

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

    def has_delete_permission(self, request, obj=None):
        return False
