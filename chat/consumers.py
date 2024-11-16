import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Message, ChatRoom


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["chatroom_id"]
        self.room_group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        username = text_data_json["username"]
        chat_room = text_data_json["chat_room"]

        # Save message and broadcast
        chat_room_obj = await sync_to_async(ChatRoom.objects.get)(id=chat_room)
        user = await sync_to_async(User.objects.get)(username=username)
        await self.save_message(message, user, chat_room_obj)

        # Regular chat messages are always user type
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": username,
                "message_type": "user",
            },
        )

    # This method is called for system announcements
    async def system_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "username": "System",  # Add this
                    "type": "system",
                }
            )
        )

    # This method handles regular chat messages
    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "username": event["username"],
                    "type": "user",  # This is explicit now
                }
            )
        )

    @sync_to_async
    def save_message(self, message, user, chat_room):
        Message.objects.create(message=message, user=user, chat_room=chat_room)
