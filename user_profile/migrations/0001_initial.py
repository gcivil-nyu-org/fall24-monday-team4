# Generated by Django 4.2.16 on 2024-12-13 20:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
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
                ("bio", models.TextField(blank=True, null=True)),
                ("photo_key", models.CharField(blank=True, max_length=255, null=True)),
                ("file_name", models.CharField(blank=True, max_length=255, null=True)),
                ("file_type", models.CharField(blank=True, max_length=50, null=True)),
                ("is_emergency_support", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                (
                    "instagram_handle",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "twitter_handle",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "facebook_handle",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="userprofile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FamilyMembers",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                ("full_name", models.CharField(max_length=255)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="family_members",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="familymembers",
            constraint=models.UniqueConstraint(
                fields=("email", "user"), name="unique_email_per_user"
            ),
        ),
    ]
