# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-08-08 13:28
from __future__ import unicode_literals

import autodidact.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autodidact', '0002_auto_20160614_1042'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clarification',
            name='image',
            field=models.ImageField(blank=True, upload_to=autodidact.models.image_path),
        ),
    ]