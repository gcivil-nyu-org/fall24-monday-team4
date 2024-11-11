from django.urls import path

from chat.consumers import ChatConsumer
from . import views

urlpatterns = [
    path("chatrooms/<pk>/", views.chat_room, name="chat_room"),
]

websocket_urlpatterns = [
    path("ws/chat/<chatroom_id>/", ChatConsumer.as_asgi()),
]
