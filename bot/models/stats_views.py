from django.db import models
from django.utils.translation import gettext_lazy as _
from bot.models.choices import STATS_VIEWS_TYPES


class StatsViews(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'))
    type = models.CharField(_('type'), max_length=32, choices=STATS_VIEWS_TYPES)
    key = models.CharField(_('key'), max_length=32, blank=True, null=True)  # NULL means all keys
    value = models.PositiveBigIntegerField(_('value'))

    def __str__(self):
        return f'{self.channel} - {self.created}'

    class Meta:
        ordering = ('-created',)
        verbose_name = _('view')
        verbose_name_plural = _('views')
