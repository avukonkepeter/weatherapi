# Generated by Django 2.2.14 on 2021-07-16 01:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('weatherapi', '0002_auto_20200804_2315'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='weatherapi',
            options={'ordering': ('slug',)},
        ),
    ]