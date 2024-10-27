from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt  # Optional for development
from .models import UserLocation

# Show location page
@login_required(login_url='home')  # Redirects to 'home' if the user is not logged in
def show_location(request):
    return render(request, 'locations/show_location.html')

# Save user's location to the database
@csrf_exempt  # Remove this in production and use CSRF tokens instead
def save_user_location(request):
    if request.method == "POST" and request.user.is_authenticated:
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Validate and convert latitude and longitude
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'message': 'Invalid latitude or longitude'}, status=400)

        # Update or create UserLocation for the user
        UserLocation.objects.update_or_create(
            user=request.user,
            defaults={'latitude': latitude, 'longitude': longitude}
        )
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)

