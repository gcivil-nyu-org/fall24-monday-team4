# Generated by Django 4.2.16 on 2024-11-22 22:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Match",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("ACCEPTED", "Accepted"),
                            ("DECLINED", "Declined"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "chatroom",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="chat.chatroom",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserLocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=11)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=11)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("panic", models.BooleanField(default=False)),
                ("panic_message", models.TextField(blank=True, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Trip",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "start_latitude",
                    models.DecimalField(decimal_places=6, max_digits=11),
                ),
                (
                    "start_longitude",
                    models.DecimalField(decimal_places=6, max_digits=11),
                ),
                ("dest_latitude", models.DecimalField(decimal_places=6, max_digits=11)),
                (
                    "dest_longitude",
                    models.DecimalField(decimal_places=6, max_digits=11),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SEARCHING", "Searching for companion"),
                            ("MATCHED", "Matched"),
                            ("READY", "Ready to Start"),
                            ("IN_PROGRESS", "In Progress"),
                            ("COMPLETED", "Completed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="SEARCHING",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("planned_departure", models.DateTimeField()),
                (
                    "desired_companions",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "1 Companion"),
                            (2, "2 Companions"),
                            (3, "3 Companions"),
                            (4, "4 Companions"),
                        ],
                        default=1,
                    ),
                ),
                ("completion_requested", models.BooleanField(default=False)),
                ("accepted_companions_count", models.IntegerField(default=0)),
                (
                    "search_radius",
                    models.IntegerField(
                        choices=[
                            (200, "200 meters"),
                            (500, "500 meters"),
                            (750, "750 meters"),
                            (1000, "1 kilometer"),
                        ],
                        default=200,
                        help_text="Maximum distance to search for companions",
                    ),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "chatroom",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trips",
                        to="chat.chatroom",
                    ),
                ),
                (
                    "matched_companions",
                    models.ManyToManyField(
                        through="locations.Match", to="locations.trip"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="match",
            name="trip1",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="matches",
                to="locations.trip",
            ),
        ),
        migrations.AddField(
            model_name="match",
            name="trip2",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="matched_with",
                to="locations.trip",
            ),
        ),
        migrations.AddConstraint(
            model_name="trip",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "SEARCHING")),
                fields=("user",),
                name="unique_active_trip",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="match",
            unique_together={("trip1", "trip2")},
        ),
    ]
