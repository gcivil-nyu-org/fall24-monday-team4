from django.urls import path
from .views import get_data

urlpatterns = [
    path('api/data/', get_data),
]
