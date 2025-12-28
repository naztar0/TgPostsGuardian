from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html_join, format_html
from django.utils.translation import gettext_lazy as _


class LimitationAdmin(admin.ModelAdmin):
    list_display = ['title', 'channels', 'type', 'action']
    list_per_page = 25
    date_hierarchy = 'created'
    list_filter = ['type', 'action']

    fieldsets = [
        (_('parameters'), {'fields': ['title', 'type', 'action', 'hourly_distribution', 'views_difference_interval']}),
        (_('posts_views_restrictions'), {'fields': ['views', 'views_difference'], 'classes': ['posts_views']}),
        (_('stats_restrictions'), {'fields': ['stats_restrictions'], 'classes': ['stats_views']}),
        (_('validity_scope'), {'fields': ['start_date', 'end_date', 'start_after_days', 'end_after_days',
                                          'start_after_limitation', 'end_after_limitation']}),
    ]

    def channels(self, obj):
        items = format_html_join(
            '',
            '<li><a href="{}">{}</a></li>',
            ((reverse('admin:bot_channel_change', args=[x.channel_id]), x.title)
             for x in obj.channel_set.all())
        )
        if not items:
            return '-'
        return format_html('<ol class="compact">{items}</ol>', items=items)
    channels.short_description = _('channels')

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    class Media:
        js = ['admin/js/limitation.js']
