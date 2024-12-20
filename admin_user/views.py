from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count, Case, When, IntegerField
from accounts.models import UserReports, UserDocument
from utils.s3_utils import generate_presigned_url
from django.http import JsonResponse
from user_profile.models import UserProfile
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.mail import EmailMessage
from django.conf import settings
import json
from user_profile.decorators import verification_required


@login_required
@verification_required
@staff_member_required
def admin_view(request):
    users = User.objects.select_related("userprofile").all()
    active_users = (
        User.objects.select_related("userprofile")
        .filter(documents__s3_key__isnull=False)
        .distinct()
    )

    user_documents = []
    for user in active_users:
        documents = user.documents.all()
        pending_count = documents.filter(status=1).count()
        document_data = [
            {
                "filename": document.filename,
                "file_type": document.file_type,
                "created_at": document.created_at,
                "status": dict(UserDocument.STATUS_CHOICES)[document.status],
                "description": document.description,
                "document_url": generate_presigned_url(document.s3_key),
            }
            for document in documents
        ]
        if document_data:
            user_documents.append(
                {
                    "user": user,
                    "documents": document_data,
                    "pending_count": pending_count,
                }
            )

    return render(
        request,
        "admin/admin_tabs.html",
        {"users": users, "user_documents": user_documents},
    )


@login_required
@verification_required
@staff_member_required
@require_http_methods(["GET"])
def reported_users_list(request):
    reported_active_users = (
        User.objects.filter(is_active=True, reports_received__isnull=False)
        .annotate(
            total_report_count=Count("reports_received"),
            pending_report_count=Count(
                Case(
                    When(reports_received__is_acknowledged=False, then=1),
                    output_field=IntegerField(),
                )
            ),
        )
        .values(
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "pending_report_count",
            "total_report_count",
        )
    )

    return JsonResponse({"success": True, "reports": list(reported_active_users)})


@login_required
@verification_required
@staff_member_required
@require_http_methods(["GET"])
def get_user_documents(request, user_id):
    documents = UserDocument.objects.filter(user_id=user_id)
    user = get_object_or_404(User, id=user_id)
    pending_count = documents.filter(status=1).count()

    document_data = [
        {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "created_at": document.created_at,
            "status_name": document.get_status_display(),
            "status_id": document.status,
            "description": document.description,
            "document_url": generate_presigned_url(document.s3_key),
        }
        for document in documents
    ]

    return JsonResponse(
        {
            "success": True,
            "documents": document_data,
            "username": user.username,
            "pending_count": pending_count,
        },
        status=200,
    )


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def accept_document(request, user_id, document_id):
    document = get_object_or_404(UserDocument, id=document_id, user_id=user_id)
    document.status = 2
    document.save()

    document_data = {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "created_at": document.created_at,
        "status_name": document.get_status_display(),
        "status_id": document.status,
        "description": document.description,
        "document_url": generate_presigned_url(document.s3_key),
    }

    return JsonResponse({"success": True, "document": document_data})


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def reject_document(request, user_id, document_id):
    document = get_object_or_404(UserDocument, id=document_id, user_id=user_id)
    document.status = 3
    document.save()

    document_data = {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "created_at": document.created_at,
        "status_name": document.get_status_display(),
        "status_id": document.status,
        "description": document.description,
        "document_url": generate_presigned_url(document.s3_key),
    }

    return JsonResponse({"success": True, "document": document_data})


@login_required
@verification_required
@staff_member_required
@require_http_methods(["GET"])
def get_user_reports(request):
    user_id = request.GET.get("user_id")
    user = get_object_or_404(User, id=user_id)
    reports = user.reports_received.all().order_by("-created_at")

    return JsonResponse(
        {
            "user": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "id": user.id,
            },
            "reports": [
                {
                    "id": report.id,
                    "subject": report.subject,
                    "description": report.description,
                    "is_acknowledged": report.is_acknowledged,
                    "reporter_username": report.reporter.username,
                    "created_at": report.created_at.isoformat(),
                }
                for report in reports
            ],
        }
    )


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def acknowledge_report(request):
    try:
        data = json.loads(request.body)
        report_id = data.get("report_id")
        report = get_object_or_404(UserReports, id=report_id)
        report.is_acknowledged = True
        report.save()

        return JsonResponse({"success": True})
    except json.JSONDecodeError as e:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data", "errorMessage": str(e)},
            status=400,
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def deactivate_account_email(user):
    subject = "Your Account Has Been Deactivated"
    html_message = render_to_string(
        "emails/deactivate_account_email.html",
        {"first_name": user.first_name},
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def deactivate_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )

        user = get_object_or_404(User, id=user_id)
        user.is_active = False
        user.save()
        deactivate_account_email(user)
        return JsonResponse(
            {"success": True, "message": "User account deactivated successfully."}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def activate_account_email(user):
    subject = "Your Account Has Been Activated"
    website_link = settings.SITE_URL + reverse("home")
    html_message = render_to_string(
        "emails/activate_account_email.html",
        {"website_link": website_link, "first_name": user.first_name},
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def activate_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )

        user = get_object_or_404(User, id=user_id)
        user.is_active = True
        user.save()
        activate_account_email(user)
        return JsonResponse(
            {"success": True, "message": "User account activated successfully."}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def verify_account_email(user):
    subject = "Your Account Has Been Successfully Verified"
    website_link = settings.SITE_URL + reverse("home")
    html_message = render_to_string(
        "emails/verify_account_email.html",
        {"website_link": website_link, "first_name": user.first_name},
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def verify_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )

        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        user_profile.is_verified = True
        user_profile.save()

        verify_account_email(user)
        return JsonResponse(
            {"success": True, "message": "User account has been successfully verified."}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def unverify_account_email(user):
    subject = "Your Account Has Been Unauthenticated"
    html_message = render_to_string(
        "emails/unverify_account_email.html",
        {"first_name": user.first_name},
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def unverify_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )
        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        user_profile.is_verified = False
        user_profile.save()

        unverify_account_email(user)
        return JsonResponse(
            {
                "success": True,
                "message": "User account has been successfully unauthenticated.",
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def set_emergency_support(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )

        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        user_profile.is_emergency_support = True
        user_profile.save()

        return JsonResponse(
            {
                "success": True,
                "message": "User account has been successfully set as Emergency Support.",
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def unset_emergency_support(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )
        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        user_profile.is_emergency_support = False
        user_profile.save()

        return JsonResponse(
            {
                "success": True,
                "message": "User account has been successfully unset as Emergency Support.",
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def set_admin(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )

        user = get_object_or_404(User, id=user_id)

        user.is_staff = True
        user.save()

        return JsonResponse(
            {
                "success": True,
                "message": "User account has been successfully set as administrator.",
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@verification_required
@staff_member_required
@require_http_methods(["POST"])
def unset_admin(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")

        if user_id is None:
            return JsonResponse(
                {"success": False, "error": "User ID is required."}, status=400
            )
        user = get_object_or_404(User, id=user_id)

        user.is_staff = False
        user.save()

        return JsonResponse(
            {
                "success": True,
                "message": "User account has been successfully unset as administrator.",
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
