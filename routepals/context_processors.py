from utils.s3_utils import generate_presigned_url


def profile_picture(request):
    try:
        if request.user.is_authenticated and hasattr(request.user, "userprofile"):
            key = getattr(request.user.userprofile, "photo_key", None)
            if key:
                profile_picture_url = generate_presigned_url(key, expiration=86400)
                return {"profile_picture": profile_picture_url}
    except AttributeError:
        pass
    return {"profile_picture": None}
