from django.urls import path
from .views import show_location, save_user_location, create_trip, find_matches

urlpatterns = [
    path("show_location/", show_location, name="show_location"),
    path("save_location/", save_user_location, name="save_location"),
    path("create_trip/", create_trip, name="create_trip"),
    path("find_matches/", find_matches, name="find_matches"),
]
