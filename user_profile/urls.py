from django.urls import path
from . import views

urlpatterns = [
    path("myprofile/", views.profile_view, name="profile"),
]
