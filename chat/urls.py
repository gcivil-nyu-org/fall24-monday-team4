from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="chat"),
    path("chatrooms/", views.chat_room, name="chat_room"),
    path("chatrooms/<pk>/", views.chat_room, name="chat_room"),
    path("create_chat_room/", views.create_chat_room, name="create_chat_room"),
]
