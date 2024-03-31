from datetime import datetime, timedelta, timezone
from django.db import models
from django.utils.translation import gettext_lazy as _
from preferences.models import Preferences
from bot import types


class UserBot(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    user_id = models.BigIntegerField(_('id'), unique=True, primary_key=True)
    username = models.CharField(_('@username'), max_length=256, blank=True, null=True)
    first_name = models.CharField(_('first_name'), max_length=256, blank=True, null=True)
    last_name = models.CharField(_('last_name'), max_length=256, blank=True, null=True)
    phone_number = models.CharField(_('phone_number'), max_length=32, unique=True)
    ping_time = models.DateTimeField(_('ping_time_utc'), auto_now_add=True)

    def __str__(self):
        return str(self.user_id)

    class Meta:
        ordering = ('-created',)
        verbose_name = _('userbot')
        verbose_name_plural = _('userbots')


class Log(models.Model):
    TYPES = ((types.Log.DELETION, _('deletion')), (types.Log.USERNAME_CHANGE, _('username_change')))
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    type = models.CharField(_('type'), max_length=16, choices=TYPES)
    userbot = models.ForeignKey(UserBot, models.CASCADE)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name=_('channel'), blank=True, null=True)
    post_date = models.DateTimeField(_('post_date_utc'), blank=True, null=True, default=None)
    post_views = models.PositiveBigIntegerField(_('post_views'), blank=True, null=True, default=None)
    success = models.BooleanField(_('success'), default=True)

    def __str__(self):
        return str(self.type)

    class Meta:
        ordering = ('-created',)
        verbose_name = _('log')
        verbose_name_plural = _('logs')


class Channel(models.Model):
    channel_id = models.BigIntegerField(_('id'), unique=True, primary_key=True)
    title = models.CharField(_('title'), max_length=256, blank=True, null=True)
    username = models.CharField(_('@username'), max_length=256, blank=True, null=True)
    has_protected_content = models.BooleanField(_('has_protected_content'), default=False)
    last_username_change = models.DateTimeField(_('last_username_change_utc'), blank=True, null=True, default=None)
    history_days_limit = models.PositiveSmallIntegerField(_('history_days_limit'), default=30)
    delete_albums = models.BooleanField(_('delete_albums'), default=True)
    republish_today_posts = models.BooleanField(_('republish_today_deleted_posts'), default=True)
    deletions_count_for_username_change = models.PositiveSmallIntegerField(_('deletions_count_for_username_change'), default=0)
    deletions_count_for_username_change.help_text = _('deletions_count_for_username_change_help_text')
    delete_posts_after_days = models.PositiveSmallIntegerField(_('delete_all_posts_after_days'), default=90)

    @property
    def v2_id(self):
        return int(f'-100{self.channel_id}')

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = _('channel')
        verbose_name_plural = _('channels')


class Post(models.Model):
    post_date = models.DateTimeField(_('post_date_utc'))
    limitation = models.ForeignKey('Limitation', models.CASCADE, verbose_name=_('limitation'))
    post_id = models.BigIntegerField(_('id'))
    views = models.PositiveBigIntegerField(_('views'))

    def __str__(self):
        return f'{self.limitation.channel} - {self.post_id}'

    class Meta:
        ordering = ('-post_date',)
        verbose_name = _('post')
        verbose_name_plural = _('posts')


class Limitation(models.Model):
    created = models.DateTimeField(_('created_utc'), auto_now_add=True)
    channel = models.ForeignKey(Channel, models.CASCADE, verbose_name=_('channel'))
    views_for_deletion = models.PositiveBigIntegerField(_('views_for_deletion'), default=0)
    views_difference_for_deletion = models.PositiveSmallIntegerField(_('views_difference_for_deletion'), default=0)
    views_restricted_for_deletion = models.PositiveBigIntegerField(_('views_restricted_for_deletion'), default=0)
    lang_stats_restrictions = models.BooleanField(_('lang_stats_restrictions'), default=False)
    allowed_languages = models.CharField(_('allowed_languages'), max_length=256, blank=True, null=True)
    allowed_languages.help_text = _('allowed_languages_help_text')
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


class Settings(Preferences):
    admins = models.TextField(_('admin_list'), max_length=256, blank=True, null=True)
    admins.help_text = _('admins_help_text')
    chatlist_invite = models.CharField(_('chatlist_invite'), max_length=16, blank=True, null=True)
    username_suffix_length = models.PositiveSmallIntegerField(_('username_suffix_length'), default=2)
    check_post_views_interval = models.PositiveSmallIntegerField(_('check_post_views_interval_seconds'), default=60)
    check_post_deletions_interval = models.PositiveSmallIntegerField(_('check_post_deletions_interval_seconds'), default=60)
    delete_old_posts_interval = models.PositiveSmallIntegerField(_('delete_old_posts_interval_minutes'), default=60)
    username_change_cooldown = models.PositiveSmallIntegerField(_('username_change_cooldown_minutes'), default=120)
    individual_allocations = models.BooleanField(_('individual_allocations'), default=False)

    def __str__(self):
        return str(_('settings'))

    class Meta:
        verbose_name = _('list')
        verbose_name_plural = _('lists')
