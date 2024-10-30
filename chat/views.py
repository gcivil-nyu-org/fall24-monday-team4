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
            form.save()
            return redirect('index')
    else:
        form = ChatRoomForm()
    return render(request, 'chat/create_chat_room.html', {'form': form})

