# Generated by Django 2.2.14 on 2020-08-04 23:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weatherapi', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='weatherapi',
            name='token',
        ),
        migrations.AddField(
            model_name='weatherapi',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='weatherapi',
            name='slug',
            field=models.SlugField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='weatherapi',
            name='userapi',
            field=models.BooleanField(default=False),
        ),
    ]
