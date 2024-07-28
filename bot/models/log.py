from django.db import models
from django.utils.translation import gettext_lazy as _
from bot import types


class Log(models.Model):
    TYPES = ((types.Log.DELETION, _('deletion')), (types.Log.USERNAME_CHANGE, _('username_change')))
    REASONS = ((types.UsernameChangeReason.DELETIONS_LIMIT, _('deletions_limit')),
               (types.UsernameChangeReason.LANGUAGE_STATS_VIEWS_LIMIT, _('language_stats_views_limit')),
               (types.UsernameChangeReason.LANGUAGE_STATS_VIEWS_DIFFERENCE_LIMIT, _('language_stats_views_difference_limit')),
               (types.UsernameChangeReason.THIRD_PARTY_REQUEST, _('third_party_request')))
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    type = models.CharField(_('type'), max_length=16, choices=TYPES)
    userbot = models.ForeignKey('UserBot', models.CASCADE)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'), blank=True, null=True)
    post_id = models.BigIntegerField(_('post_id'), blank=True, null=True, default=None)
    post_date = models.DateTimeField(_('post_date_utc'), blank=True, null=True, default=None)
    post_views = models.PositiveBigIntegerField(_('post_views'), blank=True, null=True, default=None)
    reason = models.CharField(_('reason'), max_length=64, choices=REASONS, blank=True, null=True)
    error_message = models.CharField(_('error_message'), max_length=256, blank=True, null=True)
    success = models.BooleanField(_('success'), default=True)
    dummy = models.BooleanField(_('dummy'), default=False)

    def __str__(self):
        return self.created.strftime('%Y-%m-%d %H:%M:%S')

    class Meta:
        ordering = ('-created',)
        verbose_name = _('log')
        verbose_name_plural = _('logs')
