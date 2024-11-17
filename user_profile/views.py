from .models import UserProfile
from django.contrib.auth.models import User
from accounts.models import UserReports
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from utils.s3_utils import upload_file_to_s3, generate_presigned_url, delete_file_from_s3
import logging
import uuid
from django.http import JsonResponse

logger = logging.getLogger(__name__)


@login_required(login_url="home")
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
            "user_to_view": user_to_view
        },
    )


def upload_profile_picture(request):
    if request.method == "POST" and request.FILES.get("photo"):
        file = request.FILES["photo"]
        unique_key = str(uuid.uuid4())
        user_photo_key = request.POST.get('user_photo_key')

        try:
            if user_photo_key:
                result = delete_file_from_s3(user_photo_key)
                if not result:
                    print(f"Failed to delete old profile picture with key: {user_photo_key}")

            s3_url = upload_file_to_s3(file, unique_key)
            profile = get_object_or_404(UserProfile, user=request.user)
            profile.photo_key = unique_key
            profile.file_name = file.name
            profile.file_type = file.content_type
            profile.save()

            return JsonResponse({"success": True, "url": s3_url})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})

def report_user(request):
    if request.method == "POST":
        subject = request.POST.get("subject")
        description = request.POST.get("description")
        reported_user_id = request.POST.get('reported_user_id')

        reporter = request.user
        reported_user = User.objects.get(id=reported_user_id)

        try:
            report = UserReports(
                reporter=reporter,
                reported_user=reported_user,
                subject=subject,
                description=description
            )
            report.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error_message': str(e)})

def remove_profile_picture(request):
    user = request.user

    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return redirect('profile')

    try:
        if profile.photo_key:
            result = delete_file_from_s3(profile.photo_key)
            if not result:
                print(f"Failed to delete old profile picture with key: {profile.photo_key}")

            profile.photo_key = None
            profile.file_name = None
            profile.file_type = None
            profile.save()

            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error_message': "No profile picture to remove."})
    except Exception as e:
        return JsonResponse({'success': False, 'error_message': str(e)})