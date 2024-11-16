from pyexpat.errors import messages
from venv import logger
import h3
import uuid
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Trip, Match, UserLocation, User
from chat.models import ChatRoom
from datetime import timedelta, datetime
from django.utils.timezone import make_aware

from django.db.models import Q, F
from django.core.paginator import Paginator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from utils.pusher_client import pusher_client
from django.conf import settings


def broadcast_trip_update(trip_id, status, message):
    pusher_client.trigger(
        f'trip-{trip_id}',
        'status-update',
        {
            'status': status,
            'message': message
        }
    )


@login_required 
def update_location(request):
    if request.method == "POST":
        try:
            lat = request.POST.get("latitude")
            lng = request.POST.get("longitude")
            UserLocation.objects.update_or_create(
                user=request.user, 
                defaults={
                    "latitude": lat, 
                    "longitude": lng
                }
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
def get_trip_locations(request):
    try:
        trip = Trip.objects.get(
            user=request.user, 
            status="IN_PROGRESS"
        )
        
        # Get matched users' locations in one query
        matched_users = User.objects.filter(
            trip__in=Trip.objects.filter(
             (Q(matches__trip2=trip, matches__status="ACCEPTED") | 
                Q(matched_with__trip2=trip, matched_with__status="ACCEPTED") | 
                Q(matches__trip1=trip, matches__status="ACCEPTED") | 
                Q(matched_with__trip1=trip, matched_with__status="ACCEPTED"))
        ).distinct()).exclude(id=request.user.id)

        locations = UserLocation.objects.filter(
            user__in=matched_users
        ).values(
            'user__username', 
            'latitude', 
            'longitude', 
            'last_updated'
        )

        return JsonResponse({
            "success": True, 
            "locations": list(locations)
        })
    except Trip.DoesNotExist:
        return JsonResponse({
            "success": False, 
            "error": "No active trip found"
        })

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
                "desired_companions": int(request.POST.get("desired_companions")),
            },
        )
        return redirect("current_trip")
    return redirect("home")

@login_required
def current_trip(request):
    try:
        user_trip = Trip.objects.get(
            user=request.user,
            status__in=["SEARCHING", "MATCHED", "READY", "IN_PROGRESS"]
        )
        
        potential_matches = []
        received_matches = []
        if user_trip.status == "SEARCHING":
            # Define time window
            time_min = user_trip.planned_departure - timedelta(minutes=30)
            time_max = user_trip.planned_departure + timedelta(minutes=30)

            # Convert locations to hexagons once
            user_start_hex = h3.latlng_to_cell(
                float(user_trip.start_latitude), 
                float(user_trip.start_longitude), 
                10
            )
            user_dest_hex = h3.latlng_to_cell(
                float(user_trip.dest_latitude), 
                float(user_trip.dest_longitude), 
                10
            )
            
            # Find potential matches in one query
            potential_matches = Trip.objects.filter(
                status="SEARCHING",
                planned_departure__range=(time_min, time_max),
                desired_companions=user_trip.desired_companions,
                accepted_companions_count__lt=F('desired_companions')
            ).exclude(
                Q(user=request.user) |
                Q(matches__trip2=user_trip, matches__status="DECLINED") |  # They declined us
                Q(matched_with__trip1=user_trip, matched_with__status="DECLINED")  # We declined them
            ).exclude(
                matches__trip2=user_trip,  # No existing match attempts
            )
            
            # Filter by location
            potential_matches = [
                trip for trip in potential_matches
                if h3.latlng_to_cell(float(trip.start_latitude), float(trip.start_longitude), 10) in h3.grid_disk(user_start_hex, 2)
                and h3.latlng_to_cell(float(trip.dest_latitude), float(trip.dest_longitude), 10) in h3.grid_disk(user_dest_hex, 2)
            ]
            
            # Broadcast to all potential matches that they should refresh
            for match in potential_matches:
                broadcast_trip_update(
                    match.id,
                    "SEARCHING",
                    "New potential companion available"
                )
            
            received_matches = Match.objects.filter(
                trip2=user_trip,
                status="PENDING"
            ).select_related('trip1__user')

        return render(request, "locations/current_trip.html", {
            "user_trip": user_trip, 
            "potential_matches": potential_matches,
            "received_matches": received_matches,
            "pusher_key": settings.PUSHER_KEY,
            "pusher_cluster": settings.PUSHER_CLUSTER
        })


    except Trip.DoesNotExist:
        return render(request, "locations/current_trip.html", {
            "error": "No active trip found. Create a trip first."
        })

@login_required
def send_match_request(request):
    if request.method == "POST":
        trip_id = request.POST.get("trip_id")
        action = request.POST.get("action")
        user_trip = Trip.objects.get(user=request.user, status="SEARCHING")

        try:
            if action == "cancel":
                Match.objects.filter(
                    trip1=user_trip, 
                    trip2_id=trip_id, 
                    status="PENDING"
                ).delete()
                
                broadcast_trip_update(
                    trip_id,
                    "UNREQUESTED",
                    "New match request recinded"
                )
            else:
                Match.objects.get_or_create(
                    trip1=user_trip,
                    trip2_id=trip_id,
                    defaults={"status": "PENDING"}
                )

                broadcast_trip_update(
                    trip_id,
                    "REQUESTED",
                    "New match request received"
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

        try:
            match = Match.objects.get(
                id=match_id,
                trip2__user=request.user,  # Ensure the user owns the receiving trip
                status="PENDING"
            )

            if action == "accept":
                match.status = "ACCEPTED"
                match.save()
                
                # Update both trips atomically to MATCHED status only
                for trip in [match.trip1, match.trip2]:
                    if trip.status != "SEARCHING":
                        raise ValueError(f"Trip {trip.id} is no longer accepting matches")
                        
                    Trip.objects.filter(id=trip.id).update(
                        accepted_companions_count=F('accepted_companions_count') + 1,
                        status='MATCHED'  # Both trips should be MATCHED first
                    )
                    
                    # Broadcast update to both users
                    broadcast_trip_update(
                        trip.id, 
                        "MATCHED",
                        f"Match accepted between {match.trip1.user.username} and {match.trip2.user.username}"
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
                        name=room_name,
                        description="Trip Group Chat"
                    )
                    # Add users to chatroom
                    chat_room.users.add(match.trip1.user, match.trip2.user)
                    
                    match.chatroom = chat_room
                    match.save()
                    
                    # Link chatroom to both trips
                    match.trip1.chatroom = chat_room
                    match.trip2.chatroom = chat_room
                    match.trip1.save()
                    match.trip2.save()
            else:
                match.status = "DECLINED"
                match.save()

                # Notify the requester their request was declined
                broadcast_trip_update(
                    match.trip1.id,
                    "SEARCHING",
                    f"{request.user.username} declined your request"
                )
            
            return redirect("current_trip")

        except Match.DoesNotExist:
            messages.error(request, "Match request not found or already handled")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, "An error occurred while processing the match")
            logger.error(f"Match handling error: {str(e)}")

    return redirect("current_trip")


def send_system_message(chat_room_id, message):
    print(f"Sending system message to chat-{chat_room_id}: {message}")  # Debug line
    pusher_client.trigger(
        f'chat-{chat_room_id}',
        'message-event',
        {
            'message': message,
            'username': "System",
            'type': 'system'
        }
    )


@login_required
def start_trip(request):
    if request.method == "POST":
        trip = Trip.objects.get(
            user=request.user, 
            status__in=["MATCHED", "READY"]
        )

        # Set to READY if not already
        if trip.status == "MATCHED":
            trip.status = "READY"
            trip.save()

            # Broadcast update
            broadcast_trip_update(trip.id, "READY", f"{request.user.username} is ready to start")
            
            if trip.chatroom:
                send_system_message(
                    trip.chatroom.id, 
                    f"{request.user.username} is ready to start the trip."
                )


        # Get all matched trips in one query, including both directions of matches
        matched_trips = Trip.objects.filter(
            (Q(matches__trip2=trip, matches__status="ACCEPTED") | 
                Q(matched_with__trip2=trip, matched_with__status="ACCEPTED") | 
                Q(matches__trip1=trip, matches__status="ACCEPTED") | 
                Q(matched_with__trip1=trip, matched_with__status="ACCEPTED"))
        ).exclude(id=trip.id).distinct()

        # If all trips (including current one) are READY, update all to IN_PROGRESS
        if matched_trips.exists() and all(t.status == "READY" for t in matched_trips):
            # Update all trips to IN_PROGRESS atomically
            matched_trips.update(status="IN_PROGRESS")
            trip.status = "IN_PROGRESS"  # Update the current trip too
            trip.save() 
            
            # Broadcast update to all participants
            broadcast_trip_update(trip.id, "IN_PROGRESS", "Trip is now in progress")
            for matched_trip in matched_trips:
                broadcast_trip_update(matched_trip.id, "IN_PROGRESS", "Trip is now in progress")

            if trip.chatroom:
                send_system_message(
                    trip.chatroom.id, 
                    "All members are ready. Trip is now in progress!"
                )

        return redirect("current_trip")

@login_required
def cancel_trip(request):
    if request.method == "POST":
        try:
            trip = Trip.objects.get(
                user=request.user, 
                status__in=["SEARCHING", "MATCHED", "READY"]
            )

            # Cancel all associated matches at once
            Match.objects.filter(
                Q(trip1=trip) | Q(trip2=trip)
            ).update(status="DECLINED")

            # Update all matched trips' companion counts
            affected_trips = Trip.objects.filter(
                    (Q(matches__trip2=trip, matches__status="ACCEPTED") | 
                    Q(matched_with__trip2=trip, matched_with__status="ACCEPTED") | 
                    Q(matches__trip1=trip, matches__status="ACCEPTED") | 
                    Q(matched_with__trip1=trip, matched_with__status="ACCEPTED")),
                    status__in=["MATCHED", "READY"]
                ).exclude(id=trip.id).distinct()
            
            for affected_trip in affected_trips:
                affected_trip.accepted_companions_count = (
                    affected_trip.matches.filter(status="ACCEPTED").count()
                )
                affected_trip.status = "SEARCHING"
                affected_trip.save()
                
                broadcast_trip_update(
                    affected_trip.id,
                    "SEARCHING",
                    f"{request.user.username} has cancelled their trip"
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
                desired_companions=trip.desired_companions
            ).exclude(user=request.user)

            for match in potential_matches:
                broadcast_trip_update(
                    match.id,
                    "SEARCHING",
                    "New potential companion available"
                )

            return redirect("home")
            
        except Trip.DoesNotExist:
            pass
    return redirect("home")


@login_required
def previous_trips(request):
    trip_list = Trip.objects.filter(
        user=request.user,
        status__in=["COMPLETED", "CANCELLED"]
    ).prefetch_related(
        'matches__trip1__user',
        'matches__trip2__user',
        'chatroom'
    ).order_by("-created_at")

    paginator = Paginator(trip_list, 3)
    page = request.GET.get("page")
    trips = paginator.get_page(page)

    trips_data = [{
        "id": trip.id,
        "start_latitude": float(trip.start_latitude),
        "start_longitude": float(trip.start_longitude),
        "dest_latitude": float(trip.dest_latitude),
        "dest_longitude": float(trip.dest_longitude),
        "companions": [
            match.trip2.user.username if match.trip1 == trip else match.trip1.user.username
            for match in trip.matches.filter(status="ACCEPTED")
        ]
    } for trip in trips]

    return render(
        request,
        "locations/previous_trips.html",
        {
            "trips": trips,
            "trips_json": json.dumps(trips_data)
        }
    )


@login_required
def complete_trip(request):
    if request.method == "POST":
        trip = Trip.objects.get(
            user=request.user, 
            status="IN_PROGRESS"
        )

        if not trip.completion_requested:
            trip.completion_requested = True
            trip.save()
            
            if trip.chatroom:
                send_system_message(
                    trip.chatroom.id,
                    f"{request.user.username} has voted to complete the trip."
                )

            # Get all connected trips in one query
            matched_trips = Trip.objects.filter(
                    (Q(matches__trip2=trip, matches__status="ACCEPTED") | 
                    Q(matched_with__trip2=trip, matched_with__status="ACCEPTED") | 
                    Q(matches__trip1=trip, matches__status="ACCEPTED") | 
                    Q(matched_with__trip1=trip, matched_with__status="ACCEPTED"))
                ).distinct()


            # Count completion votes and total members
            completion_votes = matched_trips.filter(
                completion_requested=True
            ).count()
            total_members = matched_trips.count()
        
            # If majority votes for completion
            if completion_votes >= total_members / 2:
                if trip.chatroom:
                    send_system_message(
                        trip.chatroom.id,
                        "Majority has voted to complete the trip. Trip is now archived."
                    )
                # Complete all trips in one query
                matched_trips.update(
                    status="COMPLETED", 
                    completion_requested=True 
                    )
                # Broadcast completion to all participants
                for matched_trip in matched_trips:
                    broadcast_trip_update(
                        matched_trip.id, 
                        "COMPLETED",
                        "Trip has been completed"
                    )
            return redirect("previous_trips")
    return redirect("current_trip")