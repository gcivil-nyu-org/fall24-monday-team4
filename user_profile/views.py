from .models import UserProfile, FamilyMembers
from django.contrib.auth.models import User
from accounts.models import UserReports
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from utils.s3_utils import (
    upload_file_to_s3,
    generate_presigned_url,
    delete_file_from_s3,
)
import uuid
from django.http import JsonResponse
from .decorators import verification_required
from django.views.decorators.http import require_http_methods
from utils.email_utils import FamilyMemberEmails, validate_family_members_input
from django.template.loader import render_to_string
import json


@login_required(login_url="home")
@verification_required
def profile_view(request, user_id=None):
    user_to_view = None
    familyMembers = None

    if user_id is None:
        profile = get_object_or_404(UserProfile, user=request.user)
        is_user = True
        family_members = FamilyMembers.objects.filter(user=request.user)
        familyMembers = [
            {
                "id": member.id,
                "full_name": member.full_name,
                "email": member.email,
            }
            for member in family_members
        ]
    else:
        user_to_view = get_object_or_404(User, id=user_id)
        profile = get_object_or_404(UserProfile, user=user_to_view)
        is_user = user_id == request.user.id

    if request.method == "POST":
        if is_user:
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()

            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()

            new_bio = request.POST.get("bio", "").strip()
            profile.bio = new_bio
            profile.save()
            return redirect("profile")

    if profile.photo_key:
        profile_picture_url = generate_presigned_url(profile.photo_key, expiration=3600)
    else:
        profile_picture_url = None

    return render(
        request,
        "profile/user_profile.html",
        {
            "profile": profile,
            "is_user": is_user,
            "profile_picture_url": profile_picture_url,
            "user_to_view": user_to_view,
            "family_members": familyMembers,
        },
    )


@login_required(login_url="home")
@verification_required
@require_http_methods(["POST"])
def update_family_members(request):
    try:
        data = json.loads(request.body)

        # Check for duplicate emails in submitted data
        email_list = [member["email"] for member in data]
        if len(email_list) != len(set(email_list)):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Duplicate email addresses are not allowed.",
                },
                status=400,
            )

        is_valid, error_message = validate_family_members_input(data)
        if not is_valid:
            return JsonResponse({"success": False, "error": error_message}, status=400)

        # Get existing members and create sets of emails only
        existing_members = FamilyMembers.objects.filter(user=request.user)
        existing_emails = {member.email for member in existing_members}
        new_emails = {member["email"] for member in data}

        # Find emails to remove and add
        emails_to_remove = existing_emails - new_emails
        emails_to_add = new_emails - existing_emails

        # Handle removals
        if emails_to_remove:
            removed_members = existing_members.filter(email__in=emails_to_remove)
            removed_members.delete()

            html_message_removed = render_to_string(
                "emails/removed_fam_email.html",
                {"username": request.user.username},
            )
            FamilyMemberEmails(
                list(emails_to_remove),
                html_message_removed,
                f"You've Been Removed from {request.user.username}'s Family List",
            )

        # Handle additions and updates
        for member_data in data:
            FamilyMembers.objects.update_or_create(
                user=request.user,
                email=member_data["email"],
                defaults={"full_name": member_data["name"]},
            )

        # Send welcome emails only to new members
        if emails_to_add:
            html_message_added = render_to_string(
                "emails/welcome_fam_email.html",
                {"username": request.user.username},
            )
            FamilyMemberEmails(
                list(emails_to_add),
                html_message_added,
                f"You've Been Added to {request.user.username}'s Family List",
            )

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required(login_url="home")
@verification_required
@require_http_methods(["POST"])
def upload_profile_picture(request):
    if request.FILES.get("photo"):
        file = request.FILES["photo"]

        try:
            profile = get_object_or_404(UserProfile, user=request.user)
            unique_key = str(uuid.uuid4())

            if upload_file_to_s3(file, unique_key):

                if profile.photo_key:
                    delete_file_from_s3(profile.photo_key)

                profile.photo_key = unique_key
                profile.file_name = file.name
                profile.file_type = file.content_type
                profile.save()

                return JsonResponse({"success": True})

            return JsonResponse({"success": False, "error": "Upload failed"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Photo attachment not found."})


@login_required(login_url="home")
@verification_required
@require_http_methods(["POST"])
def report_user(request):
    subject = request.POST.get("subject")
    description = request.POST.get("description")
    reported_user_id = request.POST.get("reported_user_id")
    reporter = request.user

    try:
        reported_user = User.objects.get(id=reported_user_id)

        report = UserReports(
            reporter=reporter,
            reported_user=reported_user,
            subject=subject,
            description=description,
        )
        report.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error_message": str(e)})


@login_required(login_url="home")
@verification_required
@require_http_methods(["POST"])
def remove_profile_picture(request):
    user = request.user
    try:
        profile = UserProfile.objects.get(user=user)

        if profile.photo_key:
            result = delete_file_from_s3(profile.photo_key)
            if not result:
                print(
                    f"Failed to delete old profile picture with key: {profile.photo_key}"
                )

            profile.photo_key = None
            profile.file_name = None
            profile.file_type = None
            profile.save()

            return JsonResponse({"success": True})
        return JsonResponse(
            {"success": False, "error_message": "No profile picture to remove."}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error_message": str(e)})


@login_required(login_url="home")
@verification_required
@require_http_methods(["POST"])
def update_social_handles(request):
    try:
        profile = UserProfile.objects.get(user=request.user)

        instagram = request.POST.get("instagram", "").strip() or None
        facebook = request.POST.get("facebook", "").strip() or None
        twitter = request.POST.get("twitter", "").strip() or None

        profile.instagram_handle = instagram
        profile.facebook_handle = facebook
        profile.twitter_handle = twitter
        profile.save()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error_message": str(e)})
