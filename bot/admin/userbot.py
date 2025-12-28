from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from bot.utils import admin_format_dt


class UserBotAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'username_custom', 'first_name', 'last_name', 'phone_number', 'sessions_custom']
    search_fields = ['user_id', 'username', 'first_name']
    date_hierarchy = 'created'
    list_per_page = 25

    fieldsets = [
        (_('parameters'), {'fields': ['created', 'user_id', 'username', 'first_name', 'last_name', 'phone_number',
                                      'last_service_message', 'last_service_message_date']}),
    ]

    def username_custom(self, obj):
        if obj.username:
            return format_html('<a href="tg://resolve?domain={username}">@{username}</a>', username=obj.username)
        else:
            return '-'
    username_custom.short_description = _('@username')

    def sessions_custom(self, obj):
        items = format_html_join(
            '',
            '<li><a href="{}">{}</a></li>',
            ((reverse('admin:bot_userbotsession_change', args=[x.id]), admin_format_dt(x.ping_time))
             for x in obj.userbotsession_set.all())
        )
        if not items:
            return '-'
        return format_html('<ol class="compact">{items}</ol>', items=items)
    sessions_custom.short_description = _('sessions')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False
