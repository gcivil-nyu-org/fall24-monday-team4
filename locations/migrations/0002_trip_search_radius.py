# Generated by Django 4.2.16 on 2024-11-16 04:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="search_radius",
            field=models.IntegerField(
                choices=[
                    (200, "200 meters"),
                    (500, "500 meters"),
                    (1000, "1 kilometer"),
                    (2000, "2 kilometers"),
                    (5000, "5 kilometers"),
                ],
                default=500,
                help_text="Maximum distance to search for companions",
            ),
        ),
    ]