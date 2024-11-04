from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

@login_required
def admin_view(request):
    # logger.info("hey", request.user)
    users = User.objects.all()
    # logger.debug("users: ", users)
    return render(request, "admin/admin_tabs.html", {"users": users})

def authenticate_user_page(request):
    # print("test test")
    # logger.info("hey", request.user)
    # users = User.objects.all()
    # logger.debug("users: ", users)
    # # users = User.objects.all()
    # for user in users:
    #     print(user.email)
    return render(request, "admin/authenticate_users_list.html")