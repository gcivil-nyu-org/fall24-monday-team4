from functools import wraps
from django.http import JsonResponse
from locations.models import Trip
from django.shortcuts import redirect


def active_trip_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        active_trip = Trip.objects.filter(
            user=request.user,
            status__in=["SEARCHING", "MATCHED", "READY", "IN_PROGRESS"],
        ).exists()

        if not active_trip:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": "No Active Trip Found."}, status=403
                )
            return redirect("home")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
