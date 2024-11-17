from django.shortcuts import render
from django.contrib.auth.decorators import staff_member_required
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


@staff_member_required
def admin_view(request):
    users = User.objects.all()
    return render(request, "admin/admin_tabs.html", {"users": users})

@staff_member_required
def authenticate_user_page(request):
    return render(request, "admin/authenticate_users_list.html")
