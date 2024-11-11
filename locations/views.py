import h3
import uuid
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Trip, Match, UserLocation
from chat.models import ChatRoom, Message
from datetime import timedelta, datetime
from django.utils.timezone import make_aware

# from django.db.models import Q
from django.core.paginator import Paginator


@login_required
def update_location(request):
    if request.method == "POST":
        try:
            lat = request.POST.get("latitude")
            lng = request.POST.get("longitude")
            UserLocation.objects.update_or_create(
                user=request.user, defaults={"latitude": lat, "longitude": lng}
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})


@login_required
def get_trip_locations(request):
    try:
        # Get current user's active trip
        trip = Trip.objects.get(user=request.user, status="IN_PROGRESS")

        # Get matched users' locations
        matched_users = trip.received_matches.filter(
            status="ACCEPTED", receiver__status="IN_PROGRESS"
        ).values_list("receiver__user", flat=True)

        locations = UserLocation.objects.filter(user__in=matched_users).values(
            "user__username", "latitude", "longitude", "last_updated"
        )

        return JsonResponse({"success": True, "locations": list(locations)})
    except Trip.DoesNotExist:
        return JsonResponse({"success": False, "error": "No active trip found"})


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
                "desired_companions": request.POST.get("desired_companions"),
            },
        )
        return redirect("find_matches")
    return redirect("home")


@login_required
def find_matches(request):
    try:
        # Get the current user's active trip
        user_trip = Trip.objects.filter(user=request.user, status="SEARCHING").latest(
            "created_at"
        )

        # Convert the user's start and destination locations to H3 hexagons
        user_start_hex = h3.latlng_to_cell(
            float(user_trip.start_latitude), float(user_trip.start_longitude), 10
        )
        user_dest_hex = h3.latlng_to_cell(
            float(user_trip.dest_latitude), float(user_trip.dest_longitude), 10
        )

        # Define time window
        time_min = user_trip.planned_departure - timedelta(minutes=30)
        time_max = user_trip.planned_departure + timedelta(minutes=30)

        # Get nearby hexagons
        nearby_start_hexes = set(h3.grid_disk(user_start_hex, 2))
        nearby_dest_hexes = set(h3.grid_disk(user_dest_hex, 2))

        # First get all potential matches within the time window
        time_matches = Trip.objects.filter(
            status="SEARCHING", planned_departure__range=(time_min, time_max)
        ).exclude(user=request.user)

        # Then filter by location and companion preferences
        potential_matches = []
        for trip in time_matches:
            # Check location match
            trip_start_hex = h3.latlng_to_cell(
                float(trip.start_latitude), float(trip.start_longitude), 10
            )
            trip_dest_hex = h3.latlng_to_cell(
                float(trip.dest_latitude), float(trip.dest_longitude), 10
            )

            if (
                trip_start_hex in nearby_start_hexes
                and trip_dest_hex in nearby_dest_hexes
            ):

                # Get current accepted matches count
                accepted_matches = Match.objects.filter(
                    receiver=trip, status="ACCEPTED"
                ).count()

                # Skip if trip is full
                if (
                    trip.desired_companions != 0
                    and accepted_matches >= trip.desired_companions
                ):
                    continue

                # Match if either has no preference or same number
                if (
                    user_trip.desired_companions == 0
                    or trip.desired_companions == 0
                    or user_trip.desired_companions == trip.desired_companions
                ):

                    # Add matches count info
                    trip.current_matches = accepted_matches
                    trip.spots_left = (
                        "No limit"
                        if trip.desired_companions == 0
                        else (trip.desired_companions - accepted_matches)
                    )

                    # Add existing match status checks
                    trip.has_pending_request = Match.objects.filter(
                        requester__user=request.user, receiver=trip, status="PENDING"
                    ).exists()

                    potential_matches.append(trip)

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
        action = request.POST.get("action")
        user_trip = Trip.objects.filter(user=request.user, status="SEARCHING").latest(
            "created_at"
        )

        try:
            if action == "cancel":
                Match.objects.filter(
                    requester=user_trip, receiver_id=receiver_trip_id, status="PENDING"
                ).delete()
            else:
                Match.objects.get_or_create(
                    requester=user_trip,
                    receiver_id=receiver_trip_id,
                    defaults={"status": "PENDING"},
                )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})


@login_required
def handle_match_request(request):
    if request.method == "POST":
        match_id = request.POST.get("match_id")
        action = request.POST.get("action")

        match = Match.objects.get(
            id=match_id,
            receiver__user=request.user,
            status="PENDING",
        )

        if action == "accept":
            match.status = "ACCEPTED"
            match.requester.status = "MATCHED"
            match.receiver.status = "MATCHED"

            # Check if requester already has a chatroom
            if match.requester.chatroom:
                chat_room = match.requester.chatroom
                match.receiver.chatroom = chat_room
            else:
                # Create new chatroom
                room_name = f"Trip_Group_{uuid.uuid4()}"
                chat_room = ChatRoom.objects.create(
                    name=room_name, description="Trip Group Chat"
                )
                match.requester.chatroom = chat_room
                match.receiver.chatroom = chat_room

            match.requester.save()
            match.receiver.save()
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


# locations/views.py
@login_required
def start_trip(request):
    if request.method == "POST":
        trip = Trip.objects.get(user=request.user, status="MATCHED")
        # Check again if conditions are met
        accepted_matches = trip.received_matches.filter(status="ACCEPTED").count()
        if trip.desired_companions == 0 or accepted_matches >= trip.desired_companions:
            trip.status = "IN_PROGRESS"
            trip.save()
        return redirect("find_matches")


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


@login_required
def complete_trip(request):
    if request.method == "POST":
        # Only complete trips that are IN_PROGRESS
        trip = Trip.objects.get(user=request.user, status="IN_PROGRESS")
        trip.status = "COMPLETED"
        trip.save()

        # Keep chatroom but mark trip as completed
        if trip.chatroom:
            # Optional: Add system message about trip completion
            Message.objects.create(
                chat_room=trip.chatroom,
                user=request.user,
                message="Trip has been marked as completed.",
            )

        return redirect("previous_trips")
    return redirect("find_matches")
