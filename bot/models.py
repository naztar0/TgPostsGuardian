from django.db import models
from preferences.models import Preferences
from bot import types


class UserBot(models.Model):
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    user_id = models.BigIntegerField('ID', unique=True, primary_key=True)
    username = models.CharField('@username', max_length=256, blank=True, null=True)
    first_name = models.CharField('First name', max_length=256, blank=True, null=True)
    last_name = models.CharField('Last name', max_length=256, blank=True, null=True)
    phone_number = models.CharField('Phone number', max_length=32)

    def __str__(self):
        return str(self.user_id)

    class Meta:
        ordering = ('-created',)
        verbose_name = 'userbot'
        verbose_name_plural = 'userbots'


class Log(models.Model):
    TYPES = ((types.Log.DELETION, '🗑️ Deletion'), (types.Log.USERNAME_CHANGE, '👤 Username change'))
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    type = models.CharField('Type', max_length=16, choices=TYPES)
    userbot = models.ForeignKey(UserBot, models.CASCADE)
    channel = models.ForeignKey('Channel', models.CASCADE, verbose_name='Channel', blank=True, null=True)
    post_date = models.DateTimeField('🕐 Post date, UTC', blank=True, null=True, default=None)
    post_views = models.PositiveBigIntegerField('Post views', blank=True, null=True, default=None)
    success = models.BooleanField('Success', default=True)

    def __str__(self):
        return str(self.type)

    class Meta:
        ordering = ('-created',)
        verbose_name = 'log'
        verbose_name_plural = 'logs'


class Channel(models.Model):
    channel_id = models.BigIntegerField('ID', unique=True, primary_key=True)
    title = models.CharField('Title', max_length=256, blank=True, null=True)
    username = models.CharField('@username', max_length=256, blank=True, null=True)
    has_protected_content = models.BooleanField('Has protected content', default=False)
    last_username_change = models.DateTimeField('🕐 Last username change, UTC', blank=True, null=True, default=None)
    history_days_limit = models.PositiveSmallIntegerField('History days limit', default=30)
    delete_albums = models.BooleanField('Delete albums', default=True)
    republish_today_posts = models.BooleanField('Republish today deleted posts', default=True)
    deletions_count_for_username_change = models.PositiveSmallIntegerField('Deletions count for username change', default=0)
    deletions_count_for_username_change.help_text = ('If the number of deletions is less than this value, the username will not be changed\n'
                                                     'If 0, the username will not be changed')
    delete_posts_after_days = models.PositiveSmallIntegerField('Delete all posts after days', default=90)

    @property
    def v2_id(self):
        return int(f'-100{self.channel_id}')

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = 'channel'
        verbose_name_plural = 'channels'


class Post(models.Model):
    post_date = models.DateTimeField('🕐 Post date, UTC')
    limitation = models.ForeignKey('Limitation', models.CASCADE, verbose_name='Limitation')
    post_id = models.BigIntegerField('ID')
    views = models.PositiveBigIntegerField('Views')

    def __str__(self):
        return f'{self.limitation.channel} - {self.post_id}'

    class Meta:
        ordering = ('-post_date',)
        verbose_name = 'post'
        verbose_name_plural = 'posts'


class Limitation(models.Model):
    created = models.DateTimeField('🕐 Created, UTC', auto_now_add=True)
    channel = models.ForeignKey(Channel, models.CASCADE, verbose_name='Channel')
    views_for_deletion = models.PositiveBigIntegerField('Views for deletion', default=0)
    views_difference_for_deletion = models.PositiveSmallIntegerField('Views difference for deletion, %', default=0)
    lang_stats_restrictions = models.BooleanField('Language stats restrictions', default=False)
    allowed_languages = models.CharField('Allowed languages', max_length=256, blank=True, null=True)
    allowed_languages.help_text = ('List of allowed languages separated by spaces\n'
                                   'If other languages views count is more than allowed views count, the post will be deleted')
    start_date = models.DateField('Start date, UTC', blank=True, null=True)
    end_date = models.DateField('End date, UTC', blank=True, null=True)
    start_after_days = models.PositiveIntegerField('Start after days', default=0)
    end_after_days = models.PositiveIntegerField('End after days', default=0)

    def __str__(self):
        return str(self.channel)

    class Meta:
        ordering = ('-created',)
        verbose_name = 'limitation'
        verbose_name_plural = 'limitations'


class Settings(Preferences):
    admins = models.TextField('Admin list', max_length=256, blank=True, null=True)
    admins.help_text = 'List of admin IDs separated by spaces or line breaks'
    chatlist_invite = models.CharField('Chatlist invite', max_length=16, blank=True, null=True)
    username_suffix_length = models.PositiveSmallIntegerField('Username suffix length', default=2)
    check_post_views_interval = models.PositiveSmallIntegerField('Check post views interval, seconds', default=60)
    check_post_deletions_interval = models.PositiveSmallIntegerField('Check post deletions interval, seconds', default=60)
    delete_old_posts_interval = models.PositiveSmallIntegerField('Delete old posts interval, minutes', default=60)
    username_change_cooldown = models.PositiveSmallIntegerField('Username change cooldown, minutes', default=120)
    individual_allocations = models.BooleanField('Individual allocations', default=True)

    def __str__(self):
        return 'Settings'

    class Meta:
        verbose_name = 'list'
        verbose_name_plural = 'lists'
