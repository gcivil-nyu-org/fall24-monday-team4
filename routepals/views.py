from django.shortcuts import redirect
from django.views.generic import TemplateView
from locations.models import Trip


class HomeView(TemplateView):
    template_name = "home.html"

    def get(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.user.userprofile.is_verified
            and request.user.userprofile.is_emergency_support
        ):
            return redirect("emergency_support")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["has_active_trip"] = Trip.objects.filter(
                user=self.request.user,
                status__in=["SEARCHING", "MATCHED", "READY", "IN_PROGRESS"],
            ).exists()
        return context
