from django.db import models
from django.utils.translation import gettext_lazy as _


class Channel(models.Model):
    channel_id = models.BigIntegerField(_('id'), unique=True, primary_key=True)
    title = models.CharField(_('title'), max_length=256, blank=True, null=True)
    username = models.CharField(_('@username'), max_length=256, blank=True, null=True)
    owner = models.ForeignKey('UserBot', models.SET_NULL, verbose_name=_('owner'), blank=True, null=True)
    has_protected_content = models.BooleanField(_('has_protected_content'), default=False)
    last_username_change = models.DateTimeField(_('last_username_change_utc'), blank=True, null=True, default=None)
    history_days_limit = models.PositiveSmallIntegerField(_('history_days_limit'), default=30)
    delete_albums = models.BooleanField(_('delete_albums'), default=True)
    republish_today_posts = models.BooleanField(_('republish_today_deleted_posts'), default=True)
    deletions_count_for_username_change = models.PositiveSmallIntegerField(_('deletions_count_for_username_change'), default=0)
    deletions_count_for_username_change.help_text = _('deletions_count_for_username_change_help_text')
    delete_posts_after_days = models.PositiveSmallIntegerField(_('delete_all_posts_after_days'), default=90)
    limitations = models.ManyToManyField('Limitation', verbose_name=_('limitations'), through='ChannelLimitation', blank=True)

    @property
    def v2_id(self):
        return int(f'-100{self.channel_id}')

    def __str__(self):
        return str(self.title or self.channel_id)

    class Meta:
        verbose_name = _('channel')
        verbose_name_plural = _('channels')


class ChannelLimitation(models.Model):
    channel = models.ForeignKey(Channel, models.CASCADE, verbose_name=_('channel'))
    limitation = models.ForeignKey('Limitation', models.CASCADE, verbose_name=_('limitation'))

    class Meta:
        verbose_name = _('limitation')
        verbose_name_plural = _('limitations')
