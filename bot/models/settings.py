from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel


class Settings(SingletonModel):
    chatlist_invite = models.CharField(_('chatlist_invite'), max_length=16, blank=True, null=True)
    archive_channel = models.BigIntegerField(_('archive_channel_id'), blank=True, null=True)
    username_suffix_length = models.PositiveSmallIntegerField(_('username_suffix_length'), default=2)
    check_post_views_interval = models.PositiveSmallIntegerField(_('check_post_views_interval_seconds'), default=60)
    check_post_deletions_interval = models.PositiveSmallIntegerField(_('check_post_deletions_interval_seconds'), default=60)
    check_stats_interval = models.PositiveSmallIntegerField(_('check_stats_interval_seconds'), default=120)
    delete_old_posts_interval = models.PositiveSmallIntegerField(_('delete_old_posts_interval_minutes'), default=60)
    username_change_cooldown = models.PositiveSmallIntegerField(_('username_change_cooldown_minutes'), default=120)
    individual_allocations = models.BooleanField(_('individual_allocations'), default=False)
    individual_allocations.help_text = _('individual_allocations_help_text')

    def __str__(self):
        return str(_('settings'))

    class Meta:
        verbose_name = _('list')
        verbose_name_plural = _('lists')
