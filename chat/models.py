from django.db import models
from django.contrib.auth.models import User
class ChatRoom(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)