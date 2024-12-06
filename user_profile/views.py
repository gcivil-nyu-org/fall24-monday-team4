from .models import UserProfile
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


@login_required(login_url="home")
@verification_required
def profile_view(request, user_id=None):
    user_to_view = None

    if user_id is None:
        profile = get_object_or_404(UserProfile, user=request.user)
        is_user = True
    else:
        user_to_view = get_object_or_404(User, id=user_id)
        profile = get_object_or_404(UserProfile, user=user_to_view)
        is_user = user_id == request.user.id

    if request.method == "POST":
        new_bio = request.POST.get("bio")
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
        },
    )


@login_required(login_url="home")
@verification_required
@require_http_methods(["POST"])
def upload_profile_picture(request):
    if request.FILES.get("photo"):
        file = request.FILES["photo"]

        try:
            profile = get_object_or_404(UserProfile, user=request.user)
            unique_key = str(uuid.uuid4())

            # First try uploading new file
            if upload_file_to_s3(file, unique_key):

                # Only delete old file if new upload succeeded
                if profile.photo_key:
                    delete_file_from_s3(profile.photo_key)

                # Update profile with new file info
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
