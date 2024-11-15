from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/trip/<str:trip_id>/", consumers.TripStatusConsumer.as_asgi()),
]