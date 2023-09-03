# Generated by Django 4.2.4 on 2023-09-02 23:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0002_alter_limitation_end_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='delete_posts_after_days',
            field=models.PositiveSmallIntegerField(default=90, verbose_name='Delete posts after days'),
        ),
        migrations.AddField(
            model_name='channel',
            name='has_protected_content',
            field=models.BooleanField(default=False, verbose_name='Has protected content'),
        ),
        migrations.AddField(
            model_name='channel',
            name='republish_today_posts',
            field=models.BooleanField(default=True, verbose_name='Republish today deleted posts'),
        ),
        migrations.AddField(
            model_name='channel',
            name='track_posts_after_days',
            field=models.PositiveSmallIntegerField(default=3, verbose_name='Track posts after days'),
        ),
        migrations.AddField(
            model_name='channel',
            name='views_difference_for_deletion',
            field=models.PositiveSmallIntegerField(default=10, verbose_name='Views difference for deletion, %'),
        ),
        migrations.AddField(
            model_name='settings',
            name='username_suffix_length',
            field=models.PositiveSmallIntegerField(default=2, verbose_name='Username suffix length'),
        ),
        migrations.AlterField(
            model_name='channel',
            name='deletions_count_for_username_change',
            field=models.PositiveSmallIntegerField(default=10, verbose_name='Deletions count for username change'),
        ),
        migrations.AlterField(
            model_name='log',
            name='post_date',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='🕐 Post date, UTC'),
        ),
    ]
