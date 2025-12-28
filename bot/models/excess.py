from django.db import models
from django.utils.translation import gettext_lazy as _
from bot.models.choices import LOG_TYPES, USERNAME_CHANGE_REASONS


class Excess(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'))
    type = models.CharField(_('type'), max_length=16, choices=LOG_TYPES)
    reason = models.CharField(_('reason'), max_length=64, choices=USERNAME_CHANGE_REASONS, blank=True, null=True)
    value = models.PositiveBigIntegerField(_('value'))

    def __str__(self):
        return f'{self.channel} - {self.created}'

    class Meta:
        ordering = ('-created',)
        verbose_name = _('excess')
        verbose_name_plural = _('excesses')
