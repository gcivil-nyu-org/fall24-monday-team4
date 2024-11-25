from django.urls import path
from . import views

urlpatterns = [
    path("adminview/", views.admin_view, name="admin_view"),
    path(
        "documents/<int:user_id>/", views.get_user_documents, name="get_user_documents"
    ),
    path(
        "accept-document/<int:user_id>/<int:document_id>/",
        views.accept_document,
        name="accept_document",
    ),
    path(
        "reject-document/<int:user_id>/<int:document_id>/",
        views.reject_document,
        name="reject_document",
    ),
    path("get-reported-users/", views.reported_users_list, name="reported_users"),
    path("get-user-reports/", views.get_user_reports, name="get_user_reports"),
    path("acknowledge-report/", views.acknowledge_report, name="acknowledge_report"),
    path("deactivate-account/", views.deactivate_account, name="deactivate_account"),
    path("activate-account/", views.activate_account, name="activate_account"),
    path("verify-account/", views.verify_account, name="verify_account"),
    path("unverify-account/", views.unverify_account, name="unverify_account"),
    path(
        "set-emergency-support/",
        views.set_emergency_support,
        name="set_emergency_support",
    ),
    path(
        "unset-emergency-support/",
        views.unset_emergency_support,
        name="unset_emergency_support",
    ),
    path("set-admin/", views.set_admin, name="set_admin"),
    path("unset-admin/", views.unset_admin, name="unset_admin"),
]
