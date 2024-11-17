# Generated by Django 4.2.16 on 2024-11-06 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="trip",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "SEARCHING")),
                fields=("user",),
                name="unique_active_trip",
            ),
        ),
    ]
