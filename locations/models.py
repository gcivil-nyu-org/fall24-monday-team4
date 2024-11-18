from django.db import models

# locations/models.py
from django.contrib.auth.models import User
from chat.models import ChatRoom


class UserLocation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=11, decimal_places=6)
    longitude = models.DecimalField(max_digits=11, decimal_places=6)
    last_updated = models.DateTimeField(auto_now=True)
    panic = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s location ({self.latitude}, {self.longitude})"


class Trip(models.Model):
    STATUS_CHOICES = [
        ("SEARCHING", "Searching for companion"),
        ("MATCHED", "Matched"),
        ("READY", "Ready to Start"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    DESIRED_COMPANIONS_CHOICES = [
        (1, "1 Companion"),
        (2, "2 Companions"),
        (3, "3 Companions"),
        (4, "4 Companions"),
    ]

    RADIUS_CHOICES = [
        (200, "200 meters"),
        (500, "500 meters"),
        (750, "750 meters"),
        (1000, "1 kilometer"),
    ]
    # Fields
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
    desired_companions = models.PositiveSmallIntegerField(
        choices=DESIRED_COMPANIONS_CHOICES, default=1
    )
    chatroom = models.ForeignKey(
        ChatRoom, null=True, on_delete=models.SET_NULL, related_name="trips"
    )
    completion_requested = models.BooleanField(default=False)
    matched_companions = models.ManyToManyField(
        "self", through="Match", symmetrical=False
    )
    accepted_companions_count = models.IntegerField(default=0)
    search_radius = models.IntegerField(
        choices=RADIUS_CHOICES,
        default=200,  # Changed from 500 to 200
        help_text="Maximum distance to search for companions",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

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

    trip1 = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="matches")
    trip2 = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="matched_with"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    chatroom = models.ForeignKey(ChatRoom, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return (
            f"Match between {self.trip1.user.username} and {self.trip2.user.username}"
        )

    class Meta:
        unique_together = ["trip1", "trip2"]  # Prevent duplicate matches
