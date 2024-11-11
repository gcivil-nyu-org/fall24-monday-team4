from django.contrib import admin
from .models import UserLocation, Trip, Match


@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ("user", "latitude", "longitude", "last_updated")
    search_fields = ("user__username",)
    list_filter = ("last_updated",)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at", "planned_departure")
    list_filter = ("status", "created_at", "planned_departure")
    search_fields = ("user__username",)
    readonly_fields = ("created_at",)
    list_per_page = 20


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("requester", "receiver", "status", "created_at", "chatroom")
    list_filter = ("status", "created_at")
    search_fields = (
        "chatroom__name",
        "requester__user__username",
        "receiver__user__username",
    )
    readonly_fields = ("created_at",)
    list_per_page = 20
