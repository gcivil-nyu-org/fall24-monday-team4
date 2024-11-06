from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
from . import views

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
    path("documents-list/", views.uploaded_documents_view, name="user_document_list"),
    path('upload_document_modal/', views.upload_document_modal, name='upload_document_modal_url'),
    path('upload_document/', views.upload_document, name='upload_document'),
]
