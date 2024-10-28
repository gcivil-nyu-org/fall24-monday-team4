from django.contrib.auth.forms import *
from django.contrib.auth import login
from django.shortcuts import render, redirect
from .forms import SignUpForm
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string

def welcomeEmail(user):
    subject = "Welcome to Our RoutePals!"
    html_message = render_to_string('emails/welcome_email.html', {
        'website_link': 'http://localhost:8000', #change this link to be specific to the real link
        'username': user.username
    })
    email = EmailMessage(subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email])
    email.content_subtype = "html"
    email.send()

# Post user account sign up form
def SignUp(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            welcomeEmail(user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})