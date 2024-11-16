from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import ChatRoom, Message
from locations.models import Match

# from .forms import ChatRoomForm, MessageForm
from django.db.models import Q


@login_required
def chat_room(request, pk):
    try:
        chat_room = ChatRoom.objects.get(pk=pk)
        is_archive = request.GET.get("archive") == "true"
        is_modal = request.GET.get("modal") == "true"

        if is_archive:
            if not Match.objects.filter(
                Q(trip1__user=request.user) | Q(trip2__user=request.user),
                Q(trip1__status="COMPLETED") | Q(trip2__status="COMPLETED"),
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
        template = "chat/chat_room_modal.html" if is_modal else "chat/chat_room.html"

        return render(
            request,
            template,
            {
                "chat_room": chat_room,
                "messages": messages,
                "is_archive": is_archive,
            },
        )
    except ChatRoom.DoesNotExist:
        return JsonResponse({"error": "Chat room not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid chat room ID"}, status=400)
