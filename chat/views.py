import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import ChatRoom, Message
from locations.models import Match, UserLocation
from utils.pusher_client import pusher_client
from django.db.models import Q
from django.conf import settings
from user_profile.decorators import verification_required
from locations.decorators import active_trip_required
from django.views.decorators.http import require_http_methods


@login_required
@verification_required
@require_http_methods(["GET"])
def chat_room(request, pk):
    try:
        chat_room = ChatRoom.objects.get(pk=pk)

        if not Match.objects.filter(
            Q(trip1__user=request.user) | Q(trip2__user=request.user),
            chatroom=chat_room,
        ).exists():
            return redirect("home")

        is_archive = request.GET.get("archive") == "true"

        if is_archive:
            if not Match.objects.filter(
                Q(trip1__user=request.user) | Q(trip2__user=request.user),
                Q(trip1__status__in=["COMPLETED", "CANCELLED"])
                | Q(trip2__status__in=["COMPLETED", "CANCELLED"]),
                chatroom=chat_room,
            ).exists():
                return redirect("previous_trips")
        else:
            valid_statuses = ["MATCHED", "READY", "IN_PROGRESS"]
            if not Match.objects.filter(
                Q(trip1__user=request.user) | Q(trip2__user=request.user),
                Q(trip1__status__in=valid_statuses)
                | Q(trip2__status__in=valid_statuses),
                chatroom=chat_room,
            ).exists():
                return redirect("current_trip")

        messages = Message.objects.filter(chat_room=chat_room).order_by("created_at")

        return render(
            request,
            "chat/chat_room_modal.html",
            {
                "chat_room": chat_room,
                "messages": messages,
                "is_archive": is_archive,
                "pusher_key": settings.PUSHER_KEY,
                "pusher_cluster": settings.PUSHER_CLUSTER,
            },
        )

    except ChatRoom.DoesNotExist:
        return JsonResponse({"error": "Chat room not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid chat room ID"}, status=400)


@login_required
@verification_required
@active_trip_required
@require_http_methods(["POST"])
def send_message(request):
    try:
        data = json.loads(request.body)
        chat_room = ChatRoom.objects.get(id=data["chat_room"])
        message_text = data["message"]

        # Create and save the message
        user_location = UserLocation.objects.filter(user=request.user).first()
        message_type = (
            "EMS_PANIC_MESSAGE" if user_location and user_location.panic else "USER"
        )

        Message.objects.create(
            chat_room=chat_room,
            user=request.user,
            message=message_text,
            message_type=message_type,
        )

        # Broadcast via Pusher
        pusher_client.trigger(
            f"chat-{chat_room.id}",
            "message-event",
            {
                "message": message_text,
                "user": {"username": request.user.username, "id": request.user.id},
                "type": (
                    "ems_panic_message"
                    if message_type == "EMS_PANIC_MESSAGE"
                    else "user"
                ),
            },
        )

        return JsonResponse({"success": True})
    except (ChatRoom.DoesNotExist, KeyError, json.JSONDecodeError) as e:
        return JsonResponse({"error": str(e)}, status=400)
