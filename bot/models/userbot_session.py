from django.db import models
from django.utils.translation import gettext_lazy as _
from bot.models.choices import SESSION_MODES


class UserBotSession(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    userbot = models.ForeignKey('UserBot', verbose_name=_('userbot'), on_delete=models.CASCADE)
    channels = models.ManyToManyField('Channel', verbose_name=_('channels'), blank=True)
    mode = models.PositiveSmallIntegerField(_('mode'), default=1, choices=SESSION_MODES)
    ping_time = models.DateTimeField(_('ping_time_utc'), auto_now_add=True)
    authorization = models.CharField(max_length=1024, blank=True, null=True)

    def __str__(self):
        return f'{self.userbot} ({self.id})'

    class Meta:
        ordering = ('-created',)
        verbose_name = _('userbot_session')
        verbose_name_plural = _('userbot_sessions')
