import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import ChatRoom, Message
from locations.models import Match
from utils.pusher_client import pusher_client
from django.db.models import Q
from django.conf import settings


@login_required
def chat_room(request, pk):
    try:
        chat_room = ChatRoom.objects.get(pk=pk)
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
def send_message(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            chat_room = ChatRoom.objects.get(id=data["chat_room"])
            message_text = data["message"]

            # Create and save the message
            Message.objects.create(
                chat_room=chat_room, user=request.user, message=message_text
            )

            # Broadcast via Pusher
            pusher_client.trigger(
                f"chat-{chat_room.id}",
                "message_event",
                {
                    "message": message_text,
                    "username": request.user.username,
                    "type": "user",
                },
            )

            return JsonResponse({"success": True})
        except (ChatRoom.DoesNotExist, KeyError, json.JSONDecodeError) as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
