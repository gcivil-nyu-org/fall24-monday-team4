from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import ChatRoom, Message
from .forms import ChatRoomForm, MessageForm

@login_required
def index(request):
    chat_rooms = ChatRoom.objects.all()
    return render(request, 'chat/index.html', {'chat_rooms': chat_rooms})

@login_required
def chat_room(request, pk):
    chat_room = ChatRoom.objects.get(pk=pk)
    if request.user not in chat_room.users.all():
        return redirect('index')  # Redirect to the index page if the user doesn't have access
    messages = Message.objects.filter(chat_room=chat_room)
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.user = request.user
            message.chat_room = chat_room
            message.save()
            return redirect('chat_room', pk=chat_room.pk)
    else:
        form = MessageForm()
    return render(request, 'chat/chat_room.html', {'chat_room': chat_room, 'messages': messages, 'form': form})

@login_required
def create_chat_room(request):
    if request.method == 'POST':
        form = ChatRoomForm(request.POST)
        if form.is_valid():
            chat_room = form.save()  # Save the ChatRoom instance to the database
            chat_room.users.add(request.user)  # Add the requesting user to the chat room
            return redirect('index')
    else:
        form = ChatRoomForm(initial={'users': [request.user.id]})
    return render(request, 'chat/create_chat_room.html', {'form': form})