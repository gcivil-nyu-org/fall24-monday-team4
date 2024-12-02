from django.urls import path
from .views import (
    handle_match_request,
    send_match_request,
    create_trip,
    current_trip,
    cancel_trip,
    previous_trips,
    emergency_support,
    trigger_panic,
    resolve_panic,
    start_trip,
    update_location,
    get_trip_locations,
    complete_trip,
    check_panic_users,
)

urlpatterns = [
    path("create_trip/", create_trip, name="create_trip"),
    path("current_trip/", current_trip, name="current_trip"),
    path("send_request/", send_match_request, name="send_match_request"),
    path("handle_request/", handle_match_request, name="handle_match_request"),
    path("cancel_trip/", cancel_trip, name="cancel_trip"),
    path("previous_trips/", previous_trips, name="previous_trips"),
    path("emergency_support/", emergency_support, name="emergency_support"),
    path("trigger_panic/", trigger_panic, name="trigger_panic"),
    path("resolve_panic/<str:panic_username>/", resolve_panic, name="resolve_panic"),
    path("start_trip/", start_trip, name="start_trip"),
    path("update_location/", update_location, name="update_location"),
    path("get_trip_locations/", get_trip_locations, name="get_trip_locations"),
    path("complete_trip/", complete_trip, name="complete_trip"),
    path("check_panic_users/", check_panic_users, name="check_panic_users"),
]
