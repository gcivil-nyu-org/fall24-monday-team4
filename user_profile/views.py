from .models import UserProfile
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
import logging

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

    return render(request, "profile/user_profile.html", {"profile": profile, "is_user": is_user})


def upload_profile_modal(request):
    return render(request, 'profile/upload_profile_picture_modal.html', {"user": request.user})
