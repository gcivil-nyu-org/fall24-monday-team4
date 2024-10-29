from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    photo_key = models.CharField(max_length=255, blank=True, null=True)

    # def __str__(self):
    #     return f"Profile for {self.user.username} ({self.user.email})"
