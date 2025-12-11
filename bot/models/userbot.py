from django.db import models
from django.utils.translation import gettext_lazy as _


class UserBot(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    user_id = models.BigIntegerField(_('id'), unique=True, primary_key=True)
    username = models.CharField(_('@username'), max_length=256, blank=True, null=True)
    first_name = models.CharField(_('first_name'), max_length=256, blank=True, null=True)
    last_name = models.CharField(_('last_name'), max_length=256, blank=True, null=True)
    phone_number = models.CharField(_('phone_number'), max_length=32, unique=True)
    ping_time = models.DateTimeField(_('ping_time_utc'), auto_now_add=True)
    channels = models.ManyToManyField('Channel', verbose_name=_('channels'), blank=True)

    def __str__(self):
        return str(self.user_id)

    class Meta:
        ordering = ('-created',)
        verbose_name = _('userbot')
        verbose_name_plural = _('userbots')
