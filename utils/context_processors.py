from user_profile.models import UserProfile


def verified_context(request):
    if request.user.is_authenticated:
        documents_verified = UserProfile.objects.filter(
            user=request.user,
            is_verified=True,
        ).exists()
    else:
        documents_verified = False
    return {"documents_verified": documents_verified}
