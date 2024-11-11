from django.urls import path
from . import views

urlpatterns = [
    path("adminview/", views.admin_view, name="admin_view"),
    # path("userlist/", views.authenticate_user_page, name="authenticate_user_tab_list"),
]
