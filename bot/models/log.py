from django.db import models
from django.utils.translation import gettext_lazy as _
from bot.models.choices import LOG_TYPES, USERNAME_CHANGE_REASONS


class Log(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    type = models.CharField(_('type'), max_length=16, choices=LOG_TYPES)
    userbot = models.ForeignKey('UserBot', models.CASCADE)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'), blank=True, null=True)
    post_id = models.BigIntegerField(_('post_id'), blank=True, null=True, default=None)
    post_date = models.DateTimeField(_('post_date_utc'), blank=True, null=True, default=None)
    post_views = models.PositiveBigIntegerField(_('post_views'), blank=True, null=True, default=None)
    reason = models.CharField(_('reason'), max_length=64, choices=USERNAME_CHANGE_REASONS, blank=True, null=True)
    limitation = models.ForeignKey('Limitation', models.SET_NULL, verbose_name=_('limitation'), blank=True, null=True)
    comment = models.CharField(_('comment'), max_length=256, blank=True, null=True)
    error_message = models.CharField(_('error_message'), max_length=256, blank=True, null=True)
    success = models.BooleanField(_('success'), default=True)

    def __str__(self):
        return self.created.strftime('%Y-%m-%d %H:%M:%S')

    class Meta:
        ordering = ('-created',)
        verbose_name = _('log')
        verbose_name_plural = _('logs')
