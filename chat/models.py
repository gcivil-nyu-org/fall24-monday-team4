# chat/models.py
from django.db import models
from django.contrib.auth.models import User


class ChatRoom(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(User, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)  # Make user nullable
    message = models.TextField()
    message_type = models.CharField(max_length=10, choices=[
        ('USER', 'User Message'),
        ('SYSTEM', 'System Alert')
    ], default='USER')
    created_at = models.DateTimeField(auto_now_add=True)
