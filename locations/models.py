from django.db import models

# locations/models.py
from django.contrib.auth.models import User


class UserLocation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=11, decimal_places=6)
    longitude = models.DecimalField(max_digits=11, decimal_places=6)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s location ({self.latitude}, {self.longitude})"


class Trip(models.Model):
    STATUS_CHOICES = [
        ("SEARCHING", "Searching for companion"),
        ("MATCHED", "Matched"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_latitude = models.DecimalField(max_digits=11, decimal_places=6)
    start_longitude = models.DecimalField(max_digits=11, decimal_places=6)
    dest_latitude = models.DecimalField(max_digits=11, decimal_places=6)
    dest_longitude = models.DecimalField(max_digits=11, decimal_places=6)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="SEARCHING"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    planned_departure = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="SEARCHING"),
                name="unique_active_trip",
            )
        ]

    def __str__(self):
        return f"{self.user.username}'s trip on {self.created_at.date()}"


class Match(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
    ]

    requester = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="requested_matches"
    )
    receiver = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="received_matches"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    room_id = models.CharField(max_length=100, unique=True, null=True)

    def __str__(self):
        return f"Match between {self.requester.user.username} and {self.receiver.user.username}"
