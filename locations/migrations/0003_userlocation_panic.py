# Generated by Django 4.2.16 on 2024-11-09 03:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userlocation",
            name="panic",
            field=models.BooleanField(default=False),
        ),
    ]
