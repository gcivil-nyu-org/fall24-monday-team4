from django.db import models
from django.contrib.auth.models import User

from utils.s3_utils import generate_presigned_url


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="userprofile"
    )
    bio = models.TextField(blank=True, null=True)
    photo_key = models.CharField(max_length=255, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)
    is_emergency_support = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    instagram_handle = models.CharField(max_length=100, blank=True, null=True)
    twitter_handle = models.CharField(max_length=100, blank=True, null=True)
    facebook_handle = models.CharField(max_length=100, blank=True, null=True)

    def get_photo_url(self):
        if self.photo_key:
            return generate_presigned_url(self.photo_key)
        return None

    def __str__(self):
        return f"Profile for {self.user.username} ({self.user.email})"


class FamilyMembers(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=254)
    full_name = models.CharField(max_length=255)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="family_members"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email", "user"], name="unique_email_per_user"
            )
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"
