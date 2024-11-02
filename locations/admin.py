# Register your models here.

from django.contrib import admin
from .models import UserLocation, Trip, Match


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at", "planned_departure")
    list_filter = ("status", "created_at")
    search_fields = ("user__username",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("requester", "receiver", "status", "created_at")
    list_filter = ("status", "created_at")


@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ("user", "latitude", "longitude", "last_updated")
