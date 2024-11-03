from django import forms
from .models import ChatRoom, Message

class ChatRoomForm(forms.ModelForm):
    class Meta:
        model = ChatRoom
        fields = ('name', 'description')

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('message',)