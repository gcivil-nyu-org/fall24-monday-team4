from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import UserLocation, Trip, Match
from datetime import timedelta
from django.utils import timezone

# Create your views here.


@login_required(login_url="home")  # This will redirect to URL pattern named 'home'
def show_location(request):
    return render(request, "locations/show_location.html")


def save_user_location(request):
    if request.method == "POST" and request.user.is_authenticated:
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        UserLocation.objects.update_or_create(
            user=request.user, defaults={"latitude": latitude, "longitude": longitude}
        )
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


@login_required
def create_trip(request):
    if request.method == "POST":
        # Get user's current location and destination from form
        Trip.objects.create(
            user=request.user,
            start_latitude=request.POST.get("start_latitude"),
            start_longitude=request.POST.get("start_longitude"),
            dest_latitude=request.POST.get("dest_latitude"),
            dest_longitude=request.POST.get("dest_longitude"),
            planned_departure=request.POST.get("planned_departure"),
        )
        return redirect("find_matches")

    return render(request, "locations/create_trip.html")


@login_required
def find_matches(request):
    try:
        user_trip = Trip.objects.filter(
            user=request.user, status="SEARCHING", planned_departure__gte=timezone.now()
        ).latest("created_at")

        # Find trips within 30 minutes of user's departure
        time_min = user_trip.planned_departure - timedelta(minutes=30)
        time_max = user_trip.planned_departure + timedelta(minutes=30)

        potential_matches = Trip.objects.filter(
            status="SEARCHING", planned_departure__range=(time_min, time_max)
        ).exclude(user=request.user)

        return render(
            request,
            "locations/find_matches.html",
            {"user_trip": user_trip, "potential_matches": potential_matches},
        )

    except Trip.DoesNotExist:
        return render(
            request,
            "locations/find_matches.html",
            {"error": "No active trip found. Create a trip first."},
        )
