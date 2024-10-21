from .models import UserProfile
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)

@login_required
def profile_view(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    # logger.debug('This is a debug message', profile.user.first_name, profile.user.last_name, profile.user.email)
    return render(request, 'profile.html', {'profile': profile})
