from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import ChatRoom, Message

# from .forms import ChatRoomForm, MessageForm
from django.db.models import Q

# @login_required
# def chat_room(request, pk):
#     chat_room = ChatRoom.objects.get(pk=pk)
#     if request.user not in chat_room.users.all():
#         return redirect(
#             "index"
#         )  # Redirect to the index page if the user doesn't have access
#     messages = Message.objects.filter(chat_room=chat_room)
#     if request.method == "POST":
#         form = MessageForm(request.POST)
#         if form.is_valid():
#             message = form.save(commit=False)
#             message.user = request.user
#             message.chat_room = chat_room
#             message.save()
#             return redirect("chat_room", pk=chat_room.pk)
#     else:
#         form = MessageForm()
#     return render(
#         request,
#         "chat/chat_room.html",
#         {"chat_room": chat_room, "messages": messages, "form": form},
#     )


@login_required
def chat_room(request, pk):
    chat_room = ChatRoom.objects.get(pk=pk)
    is_archive = request.GET.get("archive") == "true"

    # For archive mode, check if user was part of the completed trip
    if is_archive:
        if not chat_room.match_set.filter(
            Q(requester__user=request.user) | Q(receiver__user=request.user),
            Q(requester__status="COMPLETED") | Q(receiver__status="COMPLETED"),
        ).exists():
            return redirect("previous_trips")
    # For active chat, use existing checks
    else:
        if not (
            chat_room.users.filter(id=request.user.id).exists()
            or chat_room.match_set.filter(
                Q(requester__user=request.user) | Q(receiver__user=request.user),
                status="ACCEPTED",
            ).exists()
        ):
            return redirect("find_matches")

    messages = Message.objects.filter(chat_room=chat_room)
    return render(
        request,
        "chat/chat_room.html",
        {"chat_room": chat_room, "messages": messages, "is_archive": is_archive},
    )
