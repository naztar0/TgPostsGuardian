from django.utils.translation import gettext_lazy as _
from solo.admin import SingletonModelAdmin


class SettingsAdmin(SingletonModelAdmin):
    fieldsets = [
        (_('parameters'), {'fields': ['chatlist_invite', 'userbots_chat_invite', 'archive_channel', 'username_suffix_length',
                                      'check_post_views_interval', 'check_post_deletions_interval',
                                      'check_stats_interval', 'delete_old_posts_interval',
                                      'username_change_cooldown', 'individual_allocations']}),
    ]

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return True

    def has_delete_permission(self, request, obj=None):
        return False
