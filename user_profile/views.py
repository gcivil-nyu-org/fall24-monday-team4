from .models import UserProfile
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from utils.s3_utils import upload_file_to_s3, generate_presigned_url
import logging
import uuid
from django.http import JsonResponse

logger = logging.getLogger(__name__)


@login_required
def profile_view(request, user_id=None):
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
    return render(request, "profile/user_profile.html",
                  {"profile": profile, "is_user": is_user, "profile_picture_url": profile_picture_url})


def upload_profile_modal(request):
    return render(request, 'profile/upload_profile_picture_modal.html', {"user": request.user})

def upload_profile_picture(request):
    if request.method == 'POST' and request.FILES.get('photo'):
        file = request.FILES['photo']
        unique_key = str(uuid.uuid4())

        try:
            s3_url = upload_file_to_s3(file, unique_key)
            profile = get_object_or_404(UserProfile, user=request.user)
            profile.photo_key = unique_key
            profile.file_name = file.name
            profile.file_type = file.content_type
            profile.save()

            return JsonResponse({'success': True, 'url': s3_url})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})
