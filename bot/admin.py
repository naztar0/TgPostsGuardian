from django.contrib import admin
from django.utils.html import format_html
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
    username_custom.short_description = '@username'

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, *args, **kwargs):
        return False


class LogAdmin(admin.ModelAdmin):
    list_display = ['created', 'user_custom', 'type', 'channel', 'post_date']
    list_display_links = None
    list_per_page = 25

    date_hierarchy = 'created'
    search_fields = ['user__first_name', 'user__last_name', 'channel__channel_title']
    list_filter = ['type']

    def user_custom(self, obj):
        if obj.user:
            return format_html(f'<a href="/bot/user/?q={obj.user.user_id}">{obj.user.first_name}&nbsp;{obj.user.last_name}</a>')
        else:
            return '-'
    user_custom.short_description = 'User ID'

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class ChannelAdmin(admin.ModelAdmin):
    list_display = ['channel_id', 'title', 'username', 'has_protected_content', 'delete_albums', 'change_username',
                    'deletions_count_for_username_change', 'delete_posts_after_days', 'republish_today_posts',
                    'track_posts_after_days', 'views_difference_for_deletion', 'allowed_languages']
    list_per_page = 25
    list_editable = ['delete_albums', 'change_username', 'deletions_count_for_username_change', 'delete_posts_after_days',
                     'republish_today_posts', 'track_posts_after_days', 'views_difference_for_deletion', 'allowed_languages']

    search_fields = ['channel_id', 'title', 'username']
    list_filter = ['delete_albums', 'change_username', 'republish_today_posts']

    fieldsets = [
        ('Parameters', {'fields': ['channel_id', 'delete_albums', 'change_username',
                                   'deletions_count_for_username_change', 'delete_posts_after_days',
                                   'republish_today_posts', 'track_posts_after_days', 'views_difference_for_deletion',
                                   'allowed_languages']}),
    ]

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class PostAdmin(admin.ModelAdmin):
    list_display = ['post_date', 'channel', 'post_id', 'views']
    list_display_links = None
    list_per_page = 25

    search_fields = ['post_date', 'channel', 'post_id', 'views']
    list_filter = ['post_date', 'channel', 'post_id', 'views']

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class LimitationAdmin(admin.ModelAdmin):
    list_display = ['channel', 'views', 'start_date', 'end_date', 'no_start_date', 'no_end_date']
    list_display_links = None
    list_per_page = 25

    search_fields = ['channel']
    list_filter = ['no_start_date', 'no_end_date']

    fieldsets = [
        ('Parameters', {'fields': ['channel', 'views', 'start_date', 'end_date', 'no_start_date', 'no_end_date']}),
    ]

    def has_add_permission(self, *args, **kwargs):
        return True

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class SettingsAdmin(PreferencesAdmin):
    fieldsets = [
        ('Parameters', {'fields': ['admins', 'chatlist_invite', 'username_suffix_length', 'individual_allocations']}),
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
admin.site.register(models.Post, PostAdmin)
admin.site.register(models.Limitation, LimitationAdmin)
admin.site.register(models.Settings, SettingsAdmin)
