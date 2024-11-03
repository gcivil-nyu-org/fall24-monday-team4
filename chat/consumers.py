# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message

class ChatRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_room_id = self.scope['url_route']['kwargs']['pk']
        self.chat_room_group_name = f'chat_room_{self.chat_room_id}'

        await self.channel_layer.group_add(
            self.chat_room_group_name,
            self.channel_name
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        message = Message.objects.create(
            chat_room_id=self.chat_room_id,
            user=self.scope['user'],
            message=text_data
        )

        await self.channel_layer.group_send(
            self.chat_room_group_name,
            {'type': 'new_message', 'message': message}
        )

    async def new_message(self, event):
        message = event['message']
        await self.send(text_data=message.message)