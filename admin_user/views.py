from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count, BooleanField, Case, When, IntegerField
from accounts.models import UserReports, UserDocument, Status
from utils.s3_utils import generate_presigned_url
from django.http import JsonResponse
from user_profile.models import UserProfile
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)

@login_required
def admin_view(request):
    users = User.objects.select_related('userprofile').all()
    active_users = User.objects.select_related('userprofile').filter(
        Q(documents__deleted_at__isnull=True) & Q(documents__s3_key__isnull=False)
    ).distinct()

    user_documents = []

    for user in active_users:
        documents = user.documents.filter(deleted_at__isnull=True)

        pending_count = user.documents.filter(status__id=1, deleted_at__isnull=True).count()

        document_data = [
            {
                'filename': document.filename,
                'file_type': document.file_type,
                'created_at': document.created_at,
                'status': document.status,
                'description': document.description,
                'document_url': generate_presigned_url(document.s3_key),
            }
            for document in documents
        ]

        if document_data:
            user_documents.append({
                'user': user,
                'documents': document_data,
                'pending_count': pending_count,
            })

    return render(request, "admin/admin_tabs.html", {"users": users, 'user_documents': user_documents})

def reported_users_list(request):
    reported_active_users = User.objects.filter(
        is_active=True,
        reports_received__isnull=False
    ).annotate(
        total_report_count=Count('reports_received'),
        pending_report_count=Count(
            Case(
                When(reports_received__is_acknowledged=False, then=1),
                output_field=IntegerField()
            )
        )
    ).values('id', 'first_name', 'last_name', 'username', 'email', 'pending_report_count', 'total_report_count')

    return JsonResponse({"success": True, "reports": list(reported_active_users)})

def get_admin_document_list(request):
    try:
        active_users = User.objects.filter(
            Q(documents__deleted_at__isnull=True) & Q(documents__s3_key__isnull=False)
        ).distinct()

        user_documents = []

        for user in active_users:
            documents = user.documents.filter(deleted_at__isnull=True)

            pending_count = user.documents.filter(status__id=1, deleted_at__isnull=True).count()
            document_data = [
                {
                    'id': document.id,
                    'filename': document.filename,
                    'file_type': document.file_type,
                    'created_at': document.created_at,
                    'status': document.status,
                    'description': document.description,
                    'document_url': generate_presigned_url(document.s3_key),
                }
                for document in documents
            ]

            if document_data:
                user_documents.append({
                    'user': user,
                    'documents': document_data,
                    'pending_count': pending_count,
                })

        return JsonResponse({"success": True, "documents": user_documents }, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def get_user_documents(request, user_id):
    documents = UserDocument.objects.filter(user_id=user_id, deleted_at__isnull=True)
    user = get_object_or_404(User, id=user_id)
    pending_count = user.documents.filter(status__id=1, deleted_at__isnull=True).count()
    document_data = [
        {
            'id': document.id,
            'filename': document.filename,
            'file_type': document.file_type,
            'created_at': document.created_at,
            'status_name': document.status.name,
            'status_id': document.status.id,
            'description': document.description,
            'document_url': generate_presigned_url(document.s3_key),
        }
        for document in documents
    ]

    return JsonResponse({"success": True, "documents": document_data, "username": user.username, "pending_count": pending_count }, status=200)

@login_required
def accept_document(request, user_id, document_id):
    document = get_object_or_404(UserDocument, id=document_id, user_id=user_id)
    accepted_status = Status.objects.get(id=2)
    document.status = accepted_status
    document.save()

    document_data = {
        'id': document.id,
        'filename': document.filename,
        'file_type': document.file_type,
        'created_at': document.created_at,
        'status_name': document.status.name,
        'status_id': document.status.id,
        'description': document.description,
        'document_url': generate_presigned_url(document.s3_key),
    }

    return JsonResponse({"success": True, "document": document_data })

@login_required
def reject_document(request, user_id, document_id):
    document = get_object_or_404(UserDocument, id=document_id, user_id=user_id)
    rejected_status = Status.objects.get(id=3)
    document.status = rejected_status
    document.save()

    document_data = {
        'id': document.id,
        'filename': document.filename,
        'file_type': document.file_type,
        'created_at': document.created_at,
        'status_name': document.status.name,
        'status_id': document.status.id,
        'description': document.description,
        'document_url': generate_presigned_url(document.s3_key),
    }

    return JsonResponse({"success": True, "document": document_data })

@require_http_methods(["GET"])
def get_user_reports(request):
    user_id = request.GET.get('user_id')
    user = get_object_or_404(User, id=user_id)
    reports = user.reports_received.all().order_by('-created_at')

    return JsonResponse({
        'user': {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'id': user.id
        },
        'reports': [{
            'id': report.id,
            'subject': report.subject,
            'description': report.description,
            'is_acknowledged': report.is_acknowledged,
            'reporter_username': report.reporter.username,
            'created_at': report.created_at.isoformat()
        } for report in reports]
    })

@require_http_methods(["POST"])
def acknowledge_report(request):
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        report = get_object_or_404(UserReports, id=report_id)
        report.is_acknowledged = True
        report.save()

        return JsonResponse({'success': True})
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def deactivate_account_email(user):
    subject = "Your Account Has Been Deactivated"

    send_mail(
        subject=subject,
        message=(
            f"Dear {user.first_name},\n\n"
            "We wanted to inform you that your account has been deactivated. "
            "If you believe this was done in error, please contact our team.\n\n"
            "Thank you,\nRoutePals"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def deactivate_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')

        if user_id is None:
            return JsonResponse({'success': False, 'error': 'User ID is required.'}, status=400)

        user = get_object_or_404(User, id=user_id)
        user.is_active = False
        user.save()
        deactivate_account_email(user)
        return JsonResponse({'success': True, 'message': 'User account deactivated successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def activate_account_email(user):
    subject = "Your Account Has Been Activated"

    send_mail(
        subject=subject,
        message=(
            f"Dear {user.first_name},\n\n"
            "We are pleased to inform you that your account has been successfully activated. "
            "You can now log in and access your account.\n\n"
            "If you have any questions or need assistance, feel free to reach out to our team.\n\n"
            "Thank you,\nRoutePals"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def activate_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')

        if user_id is None:
            return JsonResponse({'success': False, 'error': 'User ID is required.'}, status=400)

        user = get_object_or_404(User, id=user_id)
        user.is_active = True
        user.save()
        activate_account_email(user)
        return JsonResponse({'success': True, 'message': 'User account activated successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def verify_account_email(user):
    subject = "Your Account Has Been Successfully Verified"

    send_mail(
        subject=subject,
        message=(
            f"Dear {user.first_name},\n\n"
            "Congratulations! Our team has reviewed your submitted documents, and we are delighted to inform you that your account has been successfully verified. "
            "You can now log in and enjoy the full range of services that RoutePals provides.\n\n"
            "If you have any questions or need assistance, please don’t hesitate to reach out to our support team.\n\n"
            "Thank you,\nRoutePals"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def verify_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')

        if user_id is None:
            return JsonResponse({'success': False, 'error': 'User ID is required.'}, status=400)

        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        user_profile.is_verified = True
        user_profile.save()

        verify_account_email(user)
        return JsonResponse({'success': True, 'message': 'User account has been successfully verified.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def unverify_account_email(user):
    subject = "Your Account Has Been Unauthenticated"

    send_mail(
        subject=subject,
        message=(
            f"Dear {user.first_name},\n\n"
            "We regret to inform you that your account has been unauthenticated. As a result, you will lose access to the services we provide. "
            "However, you can still log in to your account, but you will need to wait for re-authentication to regain access to all of our services.\n\n"
            "If you have any questions or need further assistance, please feel free to contact our support team.\n\n"
            "Thank you,\nRoutePals"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

def unverify_account(request):
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')

        if user_id is None:
            return JsonResponse({'success': False, 'error': 'User ID is required.'}, status=400)

        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        user_profile.is_verified = False
        user_profile.save()

        unverify_account_email(user)
        return JsonResponse({'success': True, 'message': 'User account has been successfully unauthenticated.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
