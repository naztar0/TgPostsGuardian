from django.db import models
from django.utils.translation import gettext_lazy as _


class UserBot(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    user_id = models.BigIntegerField(_('id'), unique=True, primary_key=True)
    username = models.CharField(_('@username'), max_length=256, blank=True, null=True)
    first_name = models.CharField(_('first_name'), max_length=256, blank=True, null=True)
    last_name = models.CharField(_('last_name'), max_length=256, blank=True, null=True)
    phone_number = models.CharField(_('phone_number'), max_length=32, unique=True)
    last_service_message = models.CharField(_('last_service_message'), max_length=4096, blank=True, null=True)
    last_service_message_date = models.DateTimeField(_('last_service_message_date'), blank=True, null=True)

    @property
    def fullname(self):
        return f'{self.first_name} {self.last_name or ''}'.rstrip()

    def __str__(self):
        return self.fullname

    class Meta:
        ordering = ('-created',)
        verbose_name = _('userbot')
        verbose_name_plural = _('userbots')
