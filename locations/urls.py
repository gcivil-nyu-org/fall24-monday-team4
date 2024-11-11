from django.urls import path
from .views import (
    handle_match_request,
    send_match_request,
    create_trip,
    find_matches,
    sent_requests,
    received_requests,
    cancel_trip,
    previous_trips,
    emergency_support_view,
    trigger_panic,
    cancel_panic,
)

urlpatterns = [
    path("create_trip/", create_trip, name="create_trip"),
    path("find_matches/", find_matches, name="find_matches"),
    path("send_request/", send_match_request, name="send_match_request"),
    path("handle_request/", handle_match_request, name="handle_match_request"),
    path("sent_requests/", sent_requests, name="sent_requests"),
    path("cancel_trip/", cancel_trip, name="cancel_trip"),
    path("previous_trips/", previous_trips, name="previous_trips"),
    path("received_requests/", received_requests, name="received_requests"),
    path("emergency_support/", emergency_support_view, name="emergency_support"),
    path("trigger_panic/", trigger_panic, name="trigger_panic"),
    path("cancel_panic/<str:panic_username>/", cancel_panic, name="cancel_panic"),
]
