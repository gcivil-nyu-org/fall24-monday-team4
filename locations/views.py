from django.shortcuts import render

# Create your views here.


def show_location(request):
    return render(request, "locations/show_location.html")
