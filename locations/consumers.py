import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class TripStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.trip_id = self.scope["url_route"]["kwargs"]["trip_id"]
        self.trip_group_name = f"trip_{self.trip_id}"
        
        # Join trip group
        await self.channel_layer.group_add(
            self.trip_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave trip group
        await self.channel_layer.group_discard(
            self.trip_group_name,
            self.channel_name
        )

    # Method that will broadcast status updates
    async def trip_status_update(self, event):
        # Send status update to WebSocket
        await self.send(text_data=json.dumps({
            "type": "status_update",
            "status": event["status"],
            "message": event["message"]
        }))