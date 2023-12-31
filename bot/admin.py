from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User as DjangoUser, Group as DjangoGroup
from preferences.admin import PreferencesAdmin

from bot import models

admin.site.site_header = admin.site.site_title = 'Admin panel'
admin.site.site_url = ''

admin.site.unregister(DjangoUser)
admin.site.unregister(DjangoGroup)
admin.site.enable_nav_sidebar = False


class UserBotAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_id', 'username_custom', 'first_name', 'last_name', 'phone_number']
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


class LogAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_custom', 'type', 'channel_custom', 'post_date', 'post_views', 'success']
    list_display_links = None
    list_per_page = 25

    date_hierarchy = 'created'
    search_fields = ['userbot__first_name', 'userbot__last_name', 'channel__channel_title']
    list_filter = ['type', 'success', 'channel__title']

    def user_custom(self, obj):
        if obj.userbot:
            return format_html(f'<a href="/bot/user/?q={obj.userbot.user_id}">{obj.userbot.first_name}&nbsp;{obj.userbot.last_name}</a>')
        else:
            return '-'
    user_custom.short_description = _('userbot')

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

    def has_delete_permission(self, *args, **kwargs):
        return False


class ChannelAdmin(admin.ModelAdmin):
    list_display = ['channel_id', 'title', 'username_custom', 'has_protected_content', 'last_username_change', 'history_days_limit',
                    'delete_albums', 'republish_today_posts', 'deletions_count_for_username_change', 'delete_posts_after_days']
    list_per_page = 25

    search_fields = ['channel_id', 'title', 'username']
    list_filter = ['has_protected_content', 'delete_albums', 'republish_today_posts']

    fieldsets = [
        ('Parameters', {'fields': ['channel_id', 'history_days_limit', 'delete_albums', 'republish_today_posts',
                                   'deletions_count_for_username_change', 'delete_posts_after_days']}),
    ]

    def username_custom(self, obj):
        if obj.username:
            return format_html(f'<a href="tg://resolve?domain={obj.username}">@{obj.username}</a>')
        else:
            return '-'
    username_custom.short_description = _('@username')

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class LimitationAdmin(admin.ModelAdmin):
    list_display = ['created', 'channel_custom', 'views_for_deletion', 'views_difference_for_deletion', 'lang_stats_restrictions',
                    'allowed_languages', 'start_date', 'end_date', 'start_after_days', 'end_after_days']
    list_per_page = 25

    search_fields = ['channel', 'channel__title']
    list_filter = ['lang_stats_restrictions', 'channel__title']

    fieldsets = [
        ('Parameters', {'fields': ['channel', 'views_for_deletion', 'views_difference_for_deletion', 'lang_stats_restrictions',
                                   'allowed_languages', 'start_date', 'end_date', 'start_after_days', 'end_after_days']}),
    ]

    def channel_custom(self, obj):
        if obj.channel:
            return format_html(f'<a href="/bot/channel/?q={obj.channel.channel_id}">{obj.channel.title}</a>')
        else:
            return '-'
    channel_custom.short_description = _('channel')

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class SettingsAdmin(PreferencesAdmin):
    fieldsets = [
        ('Parameters', {'fields': ['admins', 'chatlist_invite', 'username_suffix_length', 'check_post_views_interval',
                                   'check_post_deletions_interval', 'delete_old_posts_interval',
                                   'username_change_cooldown', 'individual_allocations']}),
    ]

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(models.UserBot, UserBotAdmin)
admin.site.register(models.Log, LogAdmin)
admin.site.register(models.Channel, ChannelAdmin)
admin.site.register(models.Limitation, LimitationAdmin)
admin.site.register(models.Settings, SettingsAdmin)
