from django.shortcuts import render
# from .models import Profile

def profile_view(request):
    # profile = Profile.objects.get(user=request.user)
    return render(request, 'profile.html')
