from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def verification_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_staff or request.user.userprofile.is_verified:
            return view_func(request, *args, **kwargs)
        else:
            messages.warning(
                request,
                "Access to Route Pals features is restricted to verified users.\
                      Please upload your verification documents.",
            )
            return redirect("home")

    return _wrapped_view


def emergency_support_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.userprofile.is_emergency_support:
            return view_func(request, *args, **kwargs)
        return redirect("home")

    return _wrapped_view
