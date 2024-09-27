from django.db import models
from django.utils.translation import gettext_lazy as _
from bot import types


class Excess(models.Model):
    TYPES = ((types.Log.DELETION, _('deletion')), (types.Log.USERNAME_CHANGE, _('username_change')))
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'))
    type = models.CharField(_('type'), max_length=16, choices=TYPES)
    value = models.PositiveBigIntegerField(_('value'))

    def __str__(self):
        return f'{self.channel} - {self.created}'

    class Meta:
        ordering = ('-created',)
        verbose_name = _('excess')
        verbose_name_plural = _('excesses')
