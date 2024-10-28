from django.contrib.auth.forms import *
from django.contrib.auth import login
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from .forms import SignUpForm

# Post user account sign up form
def SignUp(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

# Post change password form
class ChangePassword(PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy('home')
    template_name = 'registration/pwd_change.html'

class ResetPassword(SuccessMessageMixin, PasswordResetView):
    template_name = 'registration/pwd_reset.html'
    success_message = "We've emailed you instructions for setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy('password_reset_done')
