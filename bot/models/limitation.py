from datetime import datetime, timedelta, timezone
from django.db import models
from django.utils.translation import gettext_lazy as _
from bot.models.choices import LIMITATION_TYPES, LIMITATION_ACTIONS


class Limitation(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    title = models.CharField(_('title'), max_length=256)
    type = models.CharField(_('type'), max_length=32, choices=LIMITATION_TYPES)
    action = models.CharField(_('action'), max_length=32, choices=LIMITATION_ACTIONS)
    views = models.PositiveBigIntegerField(_('limitation_views'), default=0)
    views_difference = models.PositiveSmallIntegerField(_('limitation_views_difference'), default=0)
    views_difference_interval = models.PositiveSmallIntegerField(_('limitation_views_difference_interval_minutes'), default=60)
    stats_restrictions = models.TextField(_('stats_restrictions'), blank=True, null=True)
    stats_restrictions.help_text = _('stats_restrictions_help_text')
    hourly_distribution = models.BooleanField(_('hourly_distribution'), default=False)
    hourly_distribution.help_text = _('hourly_distribution_help_text')
    start_date = models.DateField(_('start_date_utc'), blank=True, null=True)
    end_date = models.DateField(_('end_date_utc'), blank=True, null=True)
    start_after_days = models.PositiveIntegerField(_('start_after_days'), default=0)
    end_after_days = models.PositiveIntegerField(_('end_after_days'), default=0)
    start_after_limitation = models.ForeignKey('self', models.SET_NULL, verbose_name=_('start_after_limitation'), blank=True, null=True, related_name='start_after_limitation_self')
    end_after_limitation = models.ForeignKey('self', models.SET_NULL, verbose_name=_('end_after_limitation'), blank=True, null=True, related_name='end_after_limitation_self')

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
        return datetime.min.date()

    @property
    def end(self):
        now_date = datetime.now(timezone.utc).date()
        if self.end_date:
            return self.end_date
        if self.end_after_days:
            return now_date - timedelta(days=self.end_after_days)
        return now_date

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('-created',)
        verbose_name = _('limitation')
        verbose_name_plural = _('limitations')
