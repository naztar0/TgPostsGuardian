from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class LimitationAdmin(admin.ModelAdmin):
    list_display = ['created', 'channel_custom', 'type', 'views', 'views_difference', 'lang_stats_restrictions_custom',
                    'start_date', 'end_date', 'start_after_days', 'end_after_days']
    list_per_page = 25

    search_fields = ['channel', 'channel__title']
    list_filter = ['type', 'channel__title']

    fieldsets = [
        (_('parameters'), {'fields': ['channel', 'type', 'views', 'views_difference', 'views_difference_interval',
                                      'lang_stats_restrictions', 'hourly_distribution', 'start_date', 'end_date',
                                      'start_after_days', 'end_after_days']}),
    ]

    def channel_custom(self, obj):
        if obj.channel:
            return format_html(f'<a href="/bot/channel/?q={obj.channel.channel_id}">{obj.channel.title}</a>')
        else:
            return '-'
    channel_custom.short_description = _('channel')

    def lang_stats_restrictions_custom(self, obj):
        return obj.lang_stats_restrictions or '-'
    lang_stats_restrictions_custom.short_description = _('lang_stats_restrictions')

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True
