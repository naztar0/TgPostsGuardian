from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class UserBotAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_id', 'username_custom', 'first_name', 'last_name', 'phone_number', 'ping_time']
    search_fields = ['user_id', 'username', 'first_name', 'last_name']
    date_hierarchy = 'created'
    list_display_links = None
    list_per_page = 25

    def username_custom(self, obj):
        if obj.username:
            return format_html(f'<a href="tg://resolve?domain={obj.username}">@{obj.username}</a>')
        else:
            return '-'
    username_custom.short_description = _('@username')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return False
