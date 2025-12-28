from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from bot import models


class TabularInlineNoExtra(admin.TabularInline): extra = 0
class LimitationInline(TabularInlineNoExtra): model = models.ChannelLimitation


class ChannelAdmin(admin.ModelAdmin):
    list_display = ['channel_id', 'title', 'username_custom', 'owner_custom', 'limitations_custom', 'last_username_change']
    list_per_page = 25

    search_fields = ['channel_id', 'title', 'username']
    list_filter = ['owner', 'has_protected_content', 'delete_albums', 'republish_today_posts']

    inlines = [LimitationInline]

    fieldsets = [
        (_('parameters'), {'fields': ['channel_id', 'owner', 'history_days_limit', 'delete_albums', 'republish_today_posts',
                                      'deletions_count_for_username_change', 'delete_posts_after_days']}),
    ]

    def username_custom(self, obj):
        if obj.username:
            return format_html('<a href="tg://resolve?domain={username}">@{username}</a>', username=obj.username)
        else:
            return '-'
    username_custom.short_description = _('@username')

    def owner_custom(self, obj):
        if not obj.owner:
            return '-'
        return format_html('<a href="{url}">{owner}</a>',
                           url=reverse('admin:bot_userbot_change', args=[obj.owner.user_id]),
                           owner=obj.owner)
    owner_custom.short_description = _('owner')

    def limitations_custom(self, obj):
        items = format_html_join(
            '',
            '<li><a href="{}">{}</a></li>',
            ((reverse('admin:bot_limitation_change', args=[x.id]), x.title)
             for x in obj.limitations.all())
        )
        if not items:
            return '-'
        return format_html('<ol class="compact">{items}</ol>', items=items)
    limitations_custom.short_description = _('limitations')

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True
