from django.shortcuts import render

# Create your views here.

def show_location(request):
    return render(request, 'locations/show_location.html')

"""
from django.http import JsonResponse

def save_user_location(request):
    if request.method == "POST":
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        # Save the data to your database if needed
        # Example: UserLocation.objects.create(user=request.user, latitude=latitude, longitude=longitude)
        return JsonResponse({'status': 'Location saved successfully'})
    return JsonResponse({'status': 'Invalid request'}, status=400)
"""

