from django.db import models
from django.utils.translation import gettext_lazy as _


class PostCheck(models.Model):
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'))
    post_date = models.DateTimeField(_('post_date_utc'))
    last_check = models.DateTimeField(_('last_check_utc'), auto_now_add=True)
    post_id = models.BigIntegerField(_('id'))
    views = models.PositiveBigIntegerField(_('views'))

    def __str__(self):
        return f'{self.channel} - {self.post_id}'

    class Meta:
        ordering = ('-post_date',)
        verbose_name = _('post')
        verbose_name_plural = _('posts')
