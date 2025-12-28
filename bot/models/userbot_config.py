from django.db import models
from django.utils.translation import gettext_lazy as _


class UserBotConfig(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    phone_number = models.CharField(_('phone_number'), max_length=32, primary_key=True)
    password = models.CharField(_('password'), max_length=64, blank=True, null=True)
    worker_instances = models.PositiveSmallIntegerField(_('worker_instances'), default=1)
    is_active = models.BooleanField(_('is_active'), default=True)

    def __str__(self):
        return self.phone_number

    class Meta:
        ordering = ('-created',)
        verbose_name = _('userbot')
        verbose_name_plural = _('userbots')
