from django.db import models

# locations/models.py
from django.contrib.auth.models import User

class UserLocation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=11, decimal_places=6)
    longitude = models.DecimalField(max_digits=11, decimal_places=6)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return {
            "username": self.user.username,
            "lat": self.latitude,
            "long": self.longitude
        }