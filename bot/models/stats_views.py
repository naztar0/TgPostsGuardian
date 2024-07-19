from django.db import models
from django.utils.translation import gettext_lazy as _


class StatsViews(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'))
    language = models.CharField(_('language'), max_length=32, blank=True, null=True)  # NULL means all languages
    value = models.PositiveBigIntegerField(_('value'))

    def __str__(self):
        return f'{self.channel} - {self.created}'

    class Meta:
        ordering = ('-created',)
        verbose_name = _('view')
        verbose_name_plural = _('views')
