import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Trip, Match
from datetime import timedelta, datetime
from django.utils.timezone import make_aware

# from django.db.models import Q
from django.core.paginator import Paginator


@login_required
def create_trip(request):

    if request.method == "POST":
        # Convert the naive datetime to timezone-aware
        planned_departure = make_aware(
            datetime.strptime(request.POST.get("planned_departure"), "%Y-%m-%dT%H:%M")
        )

        Trip.objects.update_or_create(
            user=request.user,
            status="SEARCHING",  # Only look for active searching trips
            defaults={
                "start_latitude": request.POST.get("start_latitude"),
                "start_longitude": request.POST.get("start_longitude"),
                "dest_latitude": request.POST.get("dest_latitude"),
                "dest_longitude": request.POST.get("dest_longitude"),
                "planned_departure": planned_departure,
            },
        )
        return redirect("find_matches")
    return redirect("home")


@login_required
def find_matches(request):
    try:
        user_trip = Trip.objects.filter(user=request.user, status="SEARCHING").latest(
            "created_at"
        )

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


@login_required
def send_match_request(request):
    if request.method == "POST":
        receiver_trip_id = request.POST.get("trip_id")
        user_trip = Trip.objects.filter(user=request.user, status="SEARCHING").latest(
            "created_at"
        )

        Match.objects.create(
            requester=user_trip, receiver_id=receiver_trip_id, status="PENDING"
        )
        return redirect("find_matches")


@login_required
def handle_match_request(request):
    if request.method == "POST":
        match_id = request.POST.get("match_id")
        action = request.POST.get("action")  # 'accept' or 'decline'

        match = Match.objects.get(
            id=match_id,
            receiver__user=request.user,  # Ensure user owns receiving trip
            status="PENDING",
        )

        if action == "accept":
            match.status = "ACCEPTED"
            # Update both trips to matched status
            match.requester.status = "MATCHED"
            match.receiver.status = "MATCHED"
            match.requester.save()
            match.receiver.save()
            match.room_id = f"chat_{match.id}"
        else:
            match.status = "DECLINED"

        match.save()
        return redirect("find_matches")


@login_required
def sent_requests(request):
    try:
        user_trip = Trip.objects.filter(
            user=request.user, status__in=["SEARCHING", "MATCHED"]
        ).latest("created_at")
        sent_matches = Match.objects.filter(requester=user_trip)
    except Trip.DoesNotExist:
        sent_matches = []

    return render(
        request, "locations/sent_requests.html", {"sent_matches": sent_matches}
    )


@login_required
def received_requests(request):
    try:
        user_trip = Trip.objects.filter(
            user=request.user, status__in=["SEARCHING", "MATCHED"]
        ).latest("created_at")
        received_matches = Match.objects.filter(receiver=user_trip)
    except Trip.DoesNotExist:
        received_matches = []

    return render(
        request,
        "locations/received_requests.html",
        {"received_matches": received_matches},
    )


# Chatroom stuff
# @login_required
# def chat_room(request, match_id):
#     match = Match.objects.get(
#         Q(requester__user=request.user) | Q(receiver__user=request.user),
#         id=match_id,
#         status="ACCEPTED",
#     )
#     return render(request, "locations/chat_room.html", {"match": match})


@login_required
def cancel_trip(request):
    if request.method == "POST":
        Trip.objects.filter(user=request.user, status="SEARCHING").update(
            status="CANCELLED"
        )
        return redirect("home")


@login_required
def previous_trips(request):
    trip_list = Trip.objects.filter(
        user=request.user, status__in=["MATCHED", "COMPLETED", "CANCELLED"]
    ).order_by("-created_at")

    paginator = Paginator(trip_list, 3)  # Show n trips per page
    page = request.GET.get("page")
    trips = paginator.get_page(page)

    trips_data = [
        {
            "id": trip.id,
            "start_latitude": float(trip.start_latitude),
            "start_longitude": float(trip.start_longitude),
            "dest_latitude": float(trip.dest_latitude),
            "dest_longitude": float(trip.dest_longitude),
        }
        for trip in trips
    ]

    return render(
        request,
        "locations/previous_trips.html",
        {"trips": trips, "trips_json": json.dumps(trips_data)},
    )
