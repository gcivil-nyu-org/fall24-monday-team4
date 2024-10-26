from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from .models import UserLocation

# Create your views here.

@login_required(login_url='home')  # This will redirect to URL pattern named 'home'
def show_location(request):
    return render(request, 'locations/show_location.html')

def save_user_location(request):
    if request.method == "POST" and request.user.is_authenticated:
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        UserLocation.objects.update_or_create(
            user=request.user,
            defaults={'latitude': latitude, 'longitude': longitude}
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)