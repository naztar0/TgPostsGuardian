# Generated by Django 4.2.4 on 2023-09-01 23:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='limitation',
            name='end_date',
            field=models.DateField(blank=True, null=True, verbose_name='End date, UTC'),
        ),
        migrations.AlterField(
            model_name='limitation',
            name='start_date',
            field=models.DateField(blank=True, null=True, verbose_name='Start date, UTC'),
        ),
    ]
