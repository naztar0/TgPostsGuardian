from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class ChannelAdmin(admin.ModelAdmin):
    list_display = ['channel_id', 'title', 'username_custom', 'owner_custom', 'has_protected_content', 'last_username_change', 'history_days_limit',
                    'delete_albums', 'republish_today_posts', 'deletions_count_for_username_change', 'delete_posts_after_days']
    list_per_page = 25

    search_fields = ['channel_id', 'title', 'username']
    list_filter = ['owner', 'has_protected_content', 'delete_albums', 'republish_today_posts']

    fieldsets = [
        (_('parameters'), {'fields': ['channel_id', 'owner', 'history_days_limit', 'delete_albums', 'republish_today_posts',
                                      'deletions_count_for_username_change', 'delete_posts_after_days']}),
    ]

    def username_custom(self, obj):
        if obj.username:
            return format_html(f'<a href="tg://resolve?domain={obj.username}">@{obj.username}</a>')
        else:
            return '-'
    username_custom.short_description = _('@username')

    def owner_custom(self, obj):
        if obj.owner:
            return format_html(f'<a href="/bot/userbot/?q={obj.owner.user_id}">{obj.owner.first_name}&nbsp;{obj.owner.last_name}</a>')
        else:
            return '-'
    owner_custom.short_description = _('owner')

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True
