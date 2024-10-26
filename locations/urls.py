from django.urls import path
from .views import show_location,save_user_location

urlpatterns = [
    path('show_location/', show_location, name='show_location'),
    path('save_location/', save_user_location, name='save_location'),
]   