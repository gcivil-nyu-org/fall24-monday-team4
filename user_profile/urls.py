from django.urls import path
from . import views

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    # path("upload_modal/", views.upload_profile_modal, name="upload_profile_modal_url"),
    path("profile/<int:user_id>/", views.profile_view, name="user_profile"),
    path(
        "upload_profile_picture/",
        views.upload_profile_picture,
        name="upload_user_profile_picture",
    ),
    path("report_user/", views.report_user, name="report_user"),
    path(
        "remove_profile_picture/",
        views.remove_profile_picture,
        name="remove_profile_picture",
    ),
]
