from django import forms
from .models import ChatRoom, Message
from django.contrib.auth.models import User

class ChatRoomForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(queryset=User.objects.all())

    class Meta:
        model = ChatRoom
        fields = ('name', 'description', 'users')
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('message',)