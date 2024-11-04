from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("signup", SignUp, name="signup"),
    path("change-password", ChangePassword.as_view(), name="password_change"),
    path("reset-password", ResetPassword.as_view(), name="password_reset"),
    path(
        "reset-password-sent",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset-password-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset-password-complete/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("admin-creation", AdminCreation, name="admin_creation"),
]
