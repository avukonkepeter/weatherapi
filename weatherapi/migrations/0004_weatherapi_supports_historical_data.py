# Generated by Django 2.2.14 on 2021-07-16 01:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weatherapi', '0003_auto_20210716_0102'),
    ]

    operations = [
        migrations.AddField(
            model_name='weatherapi',
            name='supports_historical_data',
            field=models.BooleanField(default=False),
        ),
    ]