from datetime import datetime, timedelta, timezone
from django.db import models
from django.utils.translation import gettext_lazy as _
from bot import types


class Limitation(models.Model):
    TYPES = ((types.Limitation.POST_VIEWS, _('limitation_post_views')),
             (types.Limitation.LANGUAGE_STATS, _('limitation_language_stats')))
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'))
    type = models.CharField(_('type'), max_length=32, choices=TYPES)
    views = models.PositiveBigIntegerField(_('limitation_views'), default=0)
    views_difference = models.PositiveSmallIntegerField(_('limitation_views_difference'), default=0)
    views_difference_interval = models.PositiveSmallIntegerField(_('limitation_views_difference_interval_minutes'), default=60)
    lang_stats_restrictions = models.TextField(_('lang_stats_restrictions'), max_length=256, blank=True, null=True)
    lang_stats_restrictions.help_text = _('lang_stats_restrictions_help_text')
    hourly_distribution = models.BooleanField(_('hourly_distribution'), default=False)
    hourly_distribution.help_text = _('hourly_distribution_help_text')
    start_date = models.DateField(_('start_date_utc'), blank=True, null=True)
    end_date = models.DateField(_('end_date_utc'), blank=True, null=True)
    start_after_days = models.PositiveIntegerField(_('start_after_days'), default=0)
    end_after_days = models.PositiveIntegerField(_('end_after_days'), default=0)

    @property
    def priority(self):
        if self.start_date and self.end_date:
            return 1
        elif self.start_date and self.end_after_days or self.start_after_days and self.end_date:
            return 2
        elif self.start_after_days and self.end_after_days:
            return 3
        elif self.start_date or self.end_date:
            return 4
        elif self.start_after_days or self.end_after_days:
            return 5
        return 6

    @property
    def start(self):
        now_date = datetime.now(timezone.utc).date()
        if self.start_date:
            return self.start_date
        if self.start_after_days:
            return now_date - timedelta(days=self.start_after_days)
        return datetime(1970, 1, 1).date()

    @property
    def end(self):
        now_date = datetime.now(timezone.utc).date()
        if self.end_date:
            return self.end_date
        if self.end_after_days:
            return now_date - timedelta(days=self.end_after_days)
        return now_date

    def __str__(self):
        return str(self.channel)

    class Meta:
        ordering = ('-created',)
        verbose_name = _('limitation')
        verbose_name_plural = _('limitations')
