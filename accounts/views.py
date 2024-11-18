from django.contrib.auth.forms import *
from django.contrib.auth import login
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from .models import UserDocument
from utils.decorators import restrict_admin
from utils.s3_utils import (
    upload_file_to_s3,
    generate_presigned_url,
    delete_file_from_s3,
)
import uuid
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.timezone import now
import json


def WelcomeEmail(user):
    subject = "Welcome to RoutePals!"
    website_link = settings.SITE_URL + reverse("home")
    html_message = render_to_string(
        "emails/welcome_email.html",
        {"website_link": website_link, "username": user.username},
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


def PasswordChangeConfirmationEmail(user):
    subject = "Your Password Has Been Changed"
    html_message = render_to_string(
        "emails/password_change_confirmation.html",
        {
            "username": user.username,
        },
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


# Post user account sign up form
def SignUp(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            WelcomeEmail(user)
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


# Post change password form
class ChangePassword(PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy("home")
    template_name = "registration/pwd_change.html"
    success_message = "Your password has been changed successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        PasswordChangeConfirmationEmail(self.request.user)
        return response


class ResetPassword(SuccessMessageMixin, PasswordResetView):
    template_name = "registration/password_reset_enter_email.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_message = (
        "We've emailed you instructions for setting your password, "
        "if an account exists with the email you entered. You should receive them shortly."
        " If you don't receive an email, "
        "please make sure you've entered the address you registered with,\
              and check your spam folder."
    )
    success_url = reverse_lazy("password_reset_done")

@restrict_admin
def uploaded_documents_view(request):
    documents = UserDocument.objects.filter(user=request.user, deleted_at__isnull=True)
    for document in documents:
        document.documentUrl = generate_presigned_url(document.s3_key)

    return render(
        request,
        "documents/user_document_list.html",
        {"user": request.user, "documents": documents},
    )


def upload_document_modal(request):
    return render(
        request, "documents/upload_document_modal.html", {"user": request.user}
    )


def upload_document(request):
    if request.method == "POST" and request.FILES.get("document"):
        document = request.FILES["document"]
        description = request.POST.get("fileDescription")
        user = request.user
        unique_key = str(uuid.uuid4())

        try:
            s3_url = upload_file_to_s3(document, unique_key)

            UserDocument.objects.create(
                user=user,
                filename=document.name,
                description=description,
                s3_key=unique_key,
                file_type=document.content_type,
            )

            return JsonResponse({"success": True, "url": s3_url})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


def documents_list(request):
    active_users = User.objects.filter(
        Q(documents__deleted_at__isnull=True) & Q(documents__s3_key__isnull=False)
    ).distinct()

    user_documents = []

    for user in active_users:
        documents = user.documents.filter(deleted_at__isnull=True)

        pending_count = user.documents.filter(
            status__id=1, deleted_at__isnull=True
        ).count()

        document_data = [
            {
                "filename": document.filename,
                "file_type": document.file_type,
                "created_at": document.created_at,
                "status": document.status,
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
        request, "documents/documents_list.html", {"user_documents": user_documents}
    )


def delete_document(request):
    try:
        data = json.loads(request.body)
        document_id = data.get("document_id")

        if document_id is None:
            return JsonResponse(
                {"success": False, "error": "No document with this id found."},
                status=400,
            )

        document = get_object_or_404(UserDocument, id=document_id)
        delete_file_from_s3(document.s3_key)
        document.deleted_at = now()
        document.save()

        return JsonResponse(
            {"success": True, "message": "Document has been successfully deleted."}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
