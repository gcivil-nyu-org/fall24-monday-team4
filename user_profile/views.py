from .models import UserProfile
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)


@login_required
def profile_view(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        new_bio = request.POST.get("bio")
        profile.bio = new_bio
        profile.save()
        return redirect("profile")

    return render(request, "profile/user_profile.html", {"profile": profile})


def upload_profile_modal(request):
    return render(request, 'profile/upload_profile_picture_modal.html', {"user": request.user})
