from django.urls import path
from .views import (
    handle_match_request,
    send_match_request,
    create_trip,
    find_matches,
    sent_requests,
    received_requests,
    chat_room,
)

urlpatterns = [
    path("create_trip/", create_trip, name="create_trip"),
    path("find_matches/", find_matches, name="find_matches"),
    path("send_request/", send_match_request, name="send_match_request"),
    path("handle_request/", handle_match_request, name="handle_match_request"),
    path("sent_requests/", sent_requests, name="sent_requests"),
    path("received_requests/", received_requests, name="received_requests"),
    path("chat/<int:match_id>/", chat_room, name="chat_room"),
]
