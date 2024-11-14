from django.contrib import admin
from .models import UserLocation, Trip, Match


@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ("user", "latitude", "longitude", "last_updated")
    search_fields = ("user__username",)
    list_filter = ("last_updated",)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at", "planned_departure", "accepted_companions_count")
    list_filter = ("status", "created_at", "planned_departure")
    search_fields = ("user__username",)
    readonly_fields = ("created_at", "accepted_companions_count")
    list_per_page = 20

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("trip1", "trip2", "status", "created_at", "chatroom")
    list_filter = ("status", "created_at")
    search_fields = (
        "chatroom__name",
        "trip1__user__username",
        "trip2__user__username",
    )
    readonly_fields = ("created_at",)
    list_per_page = 20