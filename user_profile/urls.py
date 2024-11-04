from django.urls import path
from . import views

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path('upload_modal/', views.upload_profile_modal, name='upload_profile_modal_url'),
    path("profile/<int:user_id>/", views.profile_view, name="user_profile"),
]
