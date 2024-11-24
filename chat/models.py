# chat/models.py
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet


class ChatRoom(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(User, related_name="chat_rooms")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    MESSAGE_TYPES = [
        ("USER", "User Message"),
        ("SYSTEM", "System Alert"),
        ("EMS_SYSTEM", "Emergency System Alert"),
        ("EMS_PANIC_MESSAGE", "Emergency Panic Message"),
    ]

    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    message = models.TextField()
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default="USER"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def encrypt_message(self, raw_message):
        f = Fernet(settings.ENCRYPTION_KEY)
        return f.encrypt(raw_message.encode()).decode()

    def decrypt_message(self):
        if self.message_type == "SYSTEM":
            return self.message
        f = Fernet(settings.ENCRYPTION_KEY)
        return f.decrypt(self.message.encode()).decode()

    def save(self, *args, **kwargs):
        if self.message_type != "SYSTEM" and not self.pk:
            self.message = self.encrypt_message(self.message)
        super().save(*args, **kwargs)

    def __str__(self):
        username = self.user.username if self.user else "System"
        return f"{username}'s message on {self.chat_room.name}"
