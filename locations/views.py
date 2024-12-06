import h3
import uuid
import json
from django.http import JsonResponse
from django.shortcuts import render, redirect

from locations.templatetags import trip_filters
from .models import Trip, Match, UserLocation
from chat.models import ChatRoom, Message
from datetime import timedelta, datetime
from django.utils.timezone import make_aware
from django.contrib.auth.models import User
from django.db.models import Q, F
from django.core.paginator import Paginator
from utils.pusher_client import pusher_client
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from user_profile.decorators import emergency_support_required, verification_required
from .decorators import active_trip_required
from django.views.decorators.http import require_http_methods


def broadcast_trip_update(trip_id, status, message):
    pusher_client.trigger(
        f"trip-{trip_id}", "status-update", {"status": status, "message": message}
    )


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def update_location(request):
    try:
        lat = request.POST.get("latitude")
        lng = request.POST.get("longitude")
        UserLocation.objects.update_or_create(
            user=request.user, defaults={"latitude": lat, "longitude": lng}
        )

        # # Add Pusher broadcast for location update
        # pusher_client.trigger(
        #     f'location-updates',
        #     'location-update',
        #     {
        #         'username': request.user.username,
        #         'latitude': lat,
        #         'longitude': lng,
        #         'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #     }
        # )

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
@active_trip_required
@require_http_methods(["GET"])
def get_trip_locations(request):
    try:
        trip = Trip.objects.get(user=request.user, status="IN_PROGRESS")

        # Get matched users' locations in one query
        matched_users = User.objects.filter(
            trip__in=Trip.objects.filter(
                (
                    Q(matches__trip2=trip, matches__status="ACCEPTED")
                    | Q(matched_with__trip2=trip, matched_with__status="ACCEPTED")
                    | Q(matches__trip1=trip, matches__status="ACCEPTED")
                    | Q(matched_with__trip1=trip, matched_with__status="ACCEPTED")
                )
            ).distinct()
        ).exclude(id=request.user.id)

        locations = UserLocation.objects.filter(user__in=matched_users).values(
            "user__username", "latitude", "longitude", "last_updated"
        )

        return JsonResponse({"success": True, "locations": list(locations)})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
@require_http_methods(["POST"])
def create_trip(request):
    planned_departure = request.POST.get("planned_departure")
    try:
        # Convert to timezone-aware datetime
        planned_departure = make_aware(
            datetime.strptime(planned_departure, "%Y-%m-%dT%H:%M")
        )

        # Validate datetime
        now = timezone.now()
        max_date = now + timedelta(days=365)  # 1 year from now

        if planned_departure < now:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Selected date and time cannot be in the past",
                }
            )
        if planned_departure > max_date:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Selected date cannot be more than 1 year in the future",
                }
            )

        # Create trip if validation passes
        Trip.objects.update_or_create(
            user=request.user,
            status="SEARCHING",
            defaults={
                "start_latitude": request.POST.get("start_latitude"),
                "start_longitude": request.POST.get("start_longitude"),
                "dest_latitude": request.POST.get("dest_latitude"),
                "dest_longitude": request.POST.get("dest_longitude"),
                "planned_departure": planned_departure,
                "desired_companions": int(request.POST.get("desired_companions")),
                "search_radius": int(request.POST.get("search_radius")),
                "start_address": request.POST.get("start_address"),
                "end_address": request.POST.get("end_address"),
            },
        )
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
def current_trip(request):
    try:
        user_trip = Trip.objects.get(
            user=request.user,
            status__in=["SEARCHING", "MATCHED", "READY", "IN_PROGRESS"],
        )

        potential_matches = []
        received_matches = []
        filtered_matches = []

        if user_trip.status == "SEARCHING":
            # Define time window
            time_min = user_trip.planned_departure - timedelta(minutes=30)
            time_max = user_trip.planned_departure + timedelta(minutes=30)

            # Find potential matches in one query without search_radius filter first
            potential_matches = (
                Trip.objects.filter(
                    status="SEARCHING",
                    planned_departure__range=(time_min, time_max),
                    desired_companions=user_trip.desired_companions,
                    accepted_companions_count__lt=F("desired_companions"),
                )
                .exclude(
                    Q(user=request.user)
                    | Q(
                        matches__trip2=user_trip, matches__status="DECLINED"
                    )  # They declined us
                    | Q(
                        matched_with__trip1=user_trip, matched_with__status="DECLINED"
                    )  # We declined them
                )
                .exclude(
                    matches__trip2=user_trip,  # No existing match attempts
                )
            )

            # Filter by location using the minimum search radius of each pair
            for potential_trip in potential_matches:
                # Use the minimum search radius of both trips
                min_radius = min(user_trip.search_radius, potential_trip.search_radius)

                # Get resolution and ring size based on minimum radius
                resolution, ring_size = get_h3_resolution_and_ring_size(min_radius)

                # Convert locations to hexagons with calculated resolution
                user_start_hex = h3.latlng_to_cell(
                    float(user_trip.start_latitude),
                    float(user_trip.start_longitude),
                    resolution,
                )
                user_dest_hex = h3.latlng_to_cell(
                    float(user_trip.dest_latitude),
                    float(user_trip.dest_longitude),
                    resolution,
                )

                potential_start_hex = h3.latlng_to_cell(
                    float(potential_trip.start_latitude),
                    float(potential_trip.start_longitude),
                    resolution,
                )
                potential_dest_hex = h3.latlng_to_cell(
                    float(potential_trip.dest_latitude),
                    float(potential_trip.dest_longitude),
                    resolution,
                )

                # Check if locations are within the minimum search radius
                if potential_start_hex in h3.grid_disk(
                    user_start_hex, ring_size
                ) and potential_dest_hex in h3.grid_disk(user_dest_hex, ring_size):
                    filtered_matches.append(potential_trip)

            received_matches = Match.objects.filter(
                trip2=user_trip, status="PENDING"
            ).select_related("trip1__user")

            for newTripMatch in filtered_matches:
                broadcast_trip_update(
                    newTripMatch.id, "SEARCHING", "New potential companion available"
                )

        return render(
            request,
            "locations/current_trip.html",
            {
                "user_trip": user_trip,
                "potential_matches": filtered_matches,
                "received_matches": received_matches,
                "pusher_key": settings.PUSHER_KEY,
                "pusher_cluster": settings.PUSHER_CLUSTER,
            },
        )

    except Exception:
        return render(
            request,
            "locations/current_trip.html",
            {"error": "No active trip found. Create a trip first."},
        )


def get_h3_resolution_and_ring_size(radius_meters):
    """
    Convert a radius in meters to appropriate H3 resolution and ring size.
    Returns (resolution, ring_size) tuple.
    """
    # H3 resolutions and their approximate edge lengths in meters
    # These are approximate values - adjust based on your needs
    resolution_map = [
        (8, 461.354684),  # ~460m
        (9, 174.375668),  # ~174m
        (10, 65.907807),  # ~66m
        (11, 24.910561),  # ~25m
        (12, 9.415526),  # ~9.4m
    ]

    # Find the appropriate resolution
    chosen_res = 10  # default
    for res, edge_length in resolution_map:
        if edge_length < radius_meters / 2:
            chosen_res = res
            break

    # Calculate ring size based on radius and edge length
    chosen_edge_length = [edge for res, edge in resolution_map if res == chosen_res][0]
    ring_size = max(1, int(radius_meters / (chosen_edge_length * 2)))

    return chosen_res, ring_size


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def send_match_request(request):
    trip_id = request.POST.get("trip_id")
    action = request.POST.get("action")

    try:
        user_trip = Trip.objects.get(user=request.user, status="SEARCHING")

        if action == "cancel":
            Match.objects.filter(
                trip1=user_trip, trip2_id=trip_id, status="PENDING"
            ).delete()

            broadcast_trip_update(trip_id, "UNREQUESTED", "New match request recinded")
        else:
            Match.objects.get_or_create(
                trip1=user_trip, trip2_id=trip_id, defaults={"status": "PENDING"}
            )

            broadcast_trip_update(trip_id, "REQUESTED", "New match request received")

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def handle_match_request(request):
    match_id = request.POST.get("match_id")
    action = request.POST.get("action")

    try:
        match = Match.objects.get(
            id=match_id,
            trip2__user=request.user,  # Ensure the user owns the receiving trip
            status="PENDING",
        )

        if action == "accept":
            match.status = "ACCEPTED"
            match.save()

            # Update both trips atomically to MATCHED status only
            for trip in [match.trip1, match.trip2]:
                if trip.status != "SEARCHING":
                    raise ValueError(f"Trip {trip.id} is no longer accepting matches")

                Trip.objects.filter(id=trip.id).update(
                    accepted_companions_count=F("accepted_companions_count") + 1,
                    status="MATCHED",  # Both trips should be MATCHED first
                )

                # Check and update status if matched
                trip.refresh_from_db()
                if trip.accepted_companions_count >= trip.desired_companions:
                    trip.status = "MATCHED"
                    trip.save()

            # Create chatroom if needed
            if not match.chatroom:
                room_name = f"Trip_Group_{uuid.uuid4()}"
                chat_room = ChatRoom.objects.create(
                    name=room_name, description="Trip Group Chat"
                )
                # Add users to chatroom
                chat_room.users.add(match.trip1.user, match.trip2.user)

                match.chatroom = chat_room
                match.save()

                Trip.objects.filter(id__in=[match.trip1.id, match.trip2.id]).update(
                    chatroom=chat_room
                )

            # Now clean up other pending requests from matched users
            other_pending = Match.objects.filter(
                (Q(trip1=match.trip1) | Q(trip1=match.trip2)), status="PENDING"
            )

            # Get affected trips before deletion
            affected_trip_ids = set(other_pending.values_list("trip2_id", flat=True))
            other_pending.delete()

            # Notify affected users who received requests
            for trip_id in affected_trip_ids:
                broadcast_trip_update(
                    trip_id,
                    "SEARCHING",
                    f"{match.trip1.user.username} is no longer available",
                )

            for trip in [match.trip1, match.trip2]:
                broadcast_trip_update(
                    trip.id,
                    "MATCHED",
                    (
                        f"Match accepted between {match.trip1.user.username} and "
                        f"{match.trip2.user.username}"
                    ),
                )
        else:
            match.status = "DECLINED"
            match.save()

            # Notify the requester their request was declined
            broadcast_trip_update(
                match.trip1.id,
                "SEARCHING",
                f"{request.user.username} declined your request",
            )
        return redirect("current_trip")
    except Match.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Match request not found or already handled"},
            status=404,
        )
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def send_system_message(chat_room, message):
    Message.objects.create(chat_room=chat_room, message=message, message_type="SYSTEM")

    pusher_client.trigger(
        f"chat-{chat_room.id}", "message-event", {"message": message, "type": "system"}
    )


def send_ems_message(chat_room, sytem_message, chat_message, user):
    Message.objects.create(
        chat_room=chat_room, message=sytem_message, message_type="EMS_SYSTEM"
    )
    Message.objects.create(
        chat_room=chat_room,
        user=user,
        message=chat_message,
        message_type="EMS_PANIC_MESSAGE",
    )

    # Send messages separately
    pusher_client.trigger(
        f"chat-{chat_room.id}",
        "message-event",
        {"message": sytem_message, "type": "ems_system"},
    )

    pusher_client.trigger(
        f"chat-{chat_room.id}",
        "message-event",
        {
            "message": chat_message,
            "username": user.username,
            "type": "ems_panic_message",
        },
    )


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def start_trip(request):
    trip = Trip.objects.get(user=request.user, status__in=["MATCHED", "READY"])

    # Set to READY if not already
    if trip.status == "MATCHED":
        trip.status = "READY"
        trip.save()

        # Broadcast update
        broadcast_trip_update(
            trip.id, "READY", f"{request.user.username} is ready to start"
        )

        if trip.chatroom:
            send_system_message(
                trip.chatroom,
                f"{request.user.username} is ready to start the trip.",
            )

    # Get all matched trips in one query, including both directions of matches
    matched_trips = (
        Trip.objects.filter(
            (
                Q(matches__trip2=trip, matches__status="ACCEPTED")
                | Q(matched_with__trip2=trip, matched_with__status="ACCEPTED")
                | Q(matches__trip1=trip, matches__status="ACCEPTED")
                | Q(matched_with__trip1=trip, matched_with__status="ACCEPTED")
            )
        )
        .exclude(id=trip.id)
        .distinct()
    )

    # If all trips (including current one) are READY, update all to IN_PROGRESS
    if matched_trips.exists() and all(t.status == "READY" for t in matched_trips):
        # Update all trips to IN_PROGRESS atomically
        matched_trips.update(status="IN_PROGRESS")
        trip.status = "IN_PROGRESS"  # Update the current trip too
        trip.save()

        # Broadcast update to all participants
        broadcast_trip_update(trip.id, "IN_PROGRESS", "Trip is now in progress")
        for matched_trip in matched_trips:
            broadcast_trip_update(
                matched_trip.id, "IN_PROGRESS", "Trip is now in progress"
            )

        if trip.chatroom:
            send_system_message(
                trip.chatroom, "All members are ready. Trip is now in progress!"
            )

    return redirect("current_trip")


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def cancel_trip(request):
    try:
        trip = Trip.objects.get(
            user=request.user, status__in=["SEARCHING", "MATCHED", "READY"]
        )

        # Update all matched trips' companion counts
        affected_trips = list(
            Trip.objects.filter(
                (
                    Q(matches__trip2=trip, matches__status="ACCEPTED")
                    | Q(matched_with__trip2=trip, matched_with__status="ACCEPTED")
                    | Q(matches__trip1=trip, matches__status="ACCEPTED")
                    | Q(matched_with__trip1=trip, matched_with__status="ACCEPTED")
                ),
                status__in=["MATCHED", "READY"],  # Add this back
            )
            .exclude(id=trip.id)
            .distinct()
        )

        # Cancel all associated matches at once
        Match.objects.filter(Q(trip1=trip) | Q(trip2=trip)).update(status="DECLINED")

        for affected_trip in affected_trips:
            affected_trip.accepted_companions_count = affected_trip.matches.filter(
                status="ACCEPTED"
            ).count()
            affected_trip.status = "SEARCHING"
            affected_trip.save()

            broadcast_trip_update(
                affected_trip.id,
                "SEARCHING",
                f"{request.user.username} has cancelled their trip",
            )

        # Update the cancelled trip
        trip.status = "CANCELLED"
        trip.accepted_companions_count = 0
        trip.save()

        # Also broadcast to potential matches who might now be compatible
        time_min = trip.planned_departure - timedelta(minutes=30)
        time_max = trip.planned_departure + timedelta(minutes=30)

        potential_matches = Trip.objects.filter(
            status="SEARCHING",
            planned_departure__range=(time_min, time_max),
            desired_companions=trip.desired_companions,
        ).exclude(user=request.user)

        for tripMatch in potential_matches:
            broadcast_trip_update(
                tripMatch.id, "SEARCHING", "New potential companion available"
            )

        return redirect("home")
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
def previous_trips(request):
    trip_list = (
        Trip.objects.filter(user=request.user, status__in=["COMPLETED", "CANCELLED"])
        .prefetch_related("matches__trip1__user", "matches__trip2__user", "chatroom")
        .order_by("-created_at")
    )

    paginator = Paginator(trip_list, 3)
    page = request.GET.get("page")
    trips = paginator.get_page(page)

    trips_data = [
        {
            "id": trip.id,
            "start_latitude": float(trip.start_latitude),
            "start_longitude": float(trip.start_longitude),
            "dest_latitude": float(trip.dest_latitude),
            "dest_longitude": float(trip.dest_longitude),
            "companions": [
                (
                    match.trip2.user.username
                    if match.trip1 == trip
                    else match.trip1.user.username
                )
                for match in trip.matches.filter(status="ACCEPTED")
            ],
        }
        for trip in trips
    ]

    return render(
        request,
        "locations/previous_trips.html",
        {"trips": trips, "trips_json": json.dumps(trips_data)},
    )


@login_required
@verification_required
@active_trip_required
@require_http_methods(["GET"])
def check_panic_users(request):
    try:
        trip = Trip.objects.get(user=request.user, status="IN_PROGRESS")
        has_panic = trip_filters.has_panic_users(trip)
        return JsonResponse({"success": True, "has_panic": has_panic})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def trigger_panic(request):
    try:
        user_location = UserLocation.objects.get(user=request.user)
        panic_locations = UserLocation.objects.filter(panic=True).select_related("user")

        active_trip = Trip.objects.get(user=request.user, status="IN_PROGRESS")

        user_location.panic = True
        user_location.panic_message = request.POST.get("initial_message")
        user_location.save()

        # Get all active panic locations for emergency support view
        locations_data = [
            {
                "id": loc.id,
                "username": loc.user.username,
                "panic_message": loc.panic_message,
                "latitude": float(loc.latitude),
                "longitude": float(loc.longitude),
            }
            for loc in panic_locations
        ]

        pusher_client.trigger(
            "emergency-channel",
            "panic-create",
            {
                "locations": locations_data,
                "active_users": UserLocation.objects.count(),
                "panic_users": panic_locations.count(),
            },
        )

        # Send ems message to their trip's chatroom
        if active_trip.chatroom:
            send_ems_message(
                active_trip.chatroom,
                f"{request.user.username} has triggered panic mode.",
                user_location.panic_message,
                request.user,
            )

        return JsonResponse({"success": True, "message": "Panic mode activated."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
@emergency_support_required
@require_http_methods(["POST"])
def resolve_panic(request, panic_username):
    try:
        user = User.objects.get(username=panic_username)
        user_location = UserLocation.objects.get(user=user)
        active_trip = Trip.objects.get(user=user, status="IN_PROGRESS")

        user_location.panic = False
        user_location.panic_message = None
        user_location.save()

        # Trigger a Pusher event to update the panic button
        pusher_client.trigger(
            "emergency-channel", "panic-resolve", {"username": panic_username}
        )

        # Send ems message to their trip's chatroom
        if active_trip.chatroom:
            send_system_message(
                active_trip.chatroom,
                f"Emergency support has resolved {user.username}'s panic request.",
            )

        return JsonResponse({"success": True, "message": "Panic mode deactivated."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@verification_required
@emergency_support_required
def emergency_support(request):
    # Fetch only the users who have panic mode activated
    user_locations = UserLocation.objects.filter(panic=True).select_related("user")

    active_user_count = UserLocation.objects.count()
    panic_user_count = user_locations.count()

    user_locations_data = [
        {
            "id": location.id,
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "username": location.user.username,
            "panic": location.panic,
            "panic_message": location.panic_message,
        }
        for location in user_locations
    ]

    return render(
        request,
        "locations/emergency_support.html",
        {
            "active_users": active_user_count,
            "panic_users": panic_user_count,
            "locations": user_locations,
            "locations_json": json.dumps(user_locations_data),
            "pusher_key": settings.PUSHER_KEY,
            "pusher_cluster": settings.PUSHER_CLUSTER,
        },
    )


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def complete_trip(request):
    trip = Trip.objects.get(user=request.user, status="IN_PROGRESS")

    if not trip.completion_requested:
        trip.completion_requested = True
        trip.save()

        if trip.chatroom:
            send_system_message(
                trip.chatroom,
                f"{request.user.username} has voted to complete the trip.",
            )

        # Get all connected trips in one query
        matched_trips = Trip.objects.filter(
            (
                Q(matches__trip2=trip, matches__status="ACCEPTED")
                | Q(matched_with__trip2=trip, matched_with__status="ACCEPTED")
                | Q(matches__trip1=trip, matches__status="ACCEPTED")
                | Q(matched_with__trip1=trip, matched_with__status="ACCEPTED")
            )
        ).distinct()

        # Count completion votes and total members
        completion_votes = matched_trips.filter(completion_requested=True).count()
        total_members = matched_trips.count()

        # If majority votes for completion
        if completion_votes >= total_members / 2:
            current_time = timezone.now()
            if trip.chatroom:
                send_system_message(
                    trip.chatroom,
                    "Majority has voted to complete the trip. Trip is now archived.",
                )

            # Complete all trips in one query
            matched_trips.update(
                status="COMPLETED",
                completion_requested=True,
                completed_at=current_time,
            )

            # Delete UserLocations for all users involved
            user_ids = matched_trips.values_list("user", flat=True)
            UserLocation.objects.filter(user__in=user_ids).delete()

            # Broadcast completion to all participants
            for matched_trip in matched_trips:
                broadcast_trip_update(
                    matched_trip.id, "COMPLETED", "Trip has been completed"
                )
        return redirect("previous_trips")
    return redirect("current_trip")
