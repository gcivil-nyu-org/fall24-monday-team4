import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Message, ChatRoom


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get room id from URL route
        self.room_id = self.scope["url_route"]["kwargs"]["chatroom_id"]
        self.room_group_name = f"chat_{self.room_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        print("text_dat_json: ", text_data_json)
        message = text_data_json["message"]
        username = text_data_json["username"]
        chat_room = text_data_json["chat_room"]
        user = await sync_to_async(User.objects.get)(username=username)
        chat_room = await sync_to_async(ChatRoom.objects.get)(name=chat_room)
        await self.save_message(message, user, chat_room)
        await self.channel_layer.group_send(
            self.roomGroupName,
            {
                "type": "sendMessage",
                "message": message,
                "username": username,
                "chat_room": chat_room.name,
            },
        )

    async def sendMessage(self, event):
        message = event["message"]
        username = event["username"]
        chat_room = event["chat_room"]
        print("chat_room: ", chat_room)
        await self.send(
            text_data=json.dumps(
                {"message": message, "username": username, "chat_room": chat_room}
            )
        )

    async def save_message(self, message, user, chat_room):
        await sync_to_async(Message.objects.create)(
            message=message, user=user, chat_room=chat_room
        )
