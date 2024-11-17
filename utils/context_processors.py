from user_profile.models import UserProfile
from locations.models import Trip


def verified_context(request):
    if request.user.is_authenticated:
        documents_verified = UserProfile.objects.filter(
            user=request.user,
            is_verified=True,
        ).exists()
    else:
        documents_verified = False
    return {"documents_verified": documents_verified}

def trip_context(request):
    if request.user.is_authenticated:
        has_active_trip = Trip.objects.filter(
                user=self.request.user,
                status__in=["SEARCHING", "MATCHED", "READY", "IN_PROGRESS"],
            ).exists()
    else:
        has_active_trip = False
    return {"has_active_trip": has_active_trip}
