from django.urls import path
from .views import show_location

urlpatterns = [
    path('show-location/', show_location, name='show_location'),
]