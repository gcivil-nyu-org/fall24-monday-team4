from django.contrib.auth.forms import *
from django.contrib.auth import login
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.shortcuts import render, redirect
from .forms import SignUpForm
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin


def WelcomeEmail(user):
    subject = "Welcome to RoutePals!"
    website_link = settings.SITE_URL + reverse("home")
    html_message = render_to_string(
        "emails/welcome_email.html",
        {"website_link": website_link, "username": user.username},
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


def PasswordChangeConfirmationEmail(user):
    subject = "Your Password Has Been Changed"
    html_message = render_to_string(
        "emails/password_change_confirmation.html",
        {
            "username": user.username,
        },
    )
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    email.content_subtype = "html"
    email.send()


# Post user account sign up form
def SignUp(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            WelcomeEmail(user)
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


# Post change password form
class ChangePassword(PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy("home")
    template_name = "registration/pwd_change.html"
    success_message = "Your password has been changed successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        PasswordChangeConfirmationEmail(self.request.user)
        return response


class ResetPassword(SuccessMessageMixin, PasswordResetView):
    template_name = "registration/password_reset_enter_email.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_message = (
        "We've emailed you instructions for setting your password, "
        "if an account exists with the email you entered. You should receive them shortly."
        " If you don't receive an email, "
        "please make sure you've entered the address you registered with,\
              and check your spam folder."
    )
    success_url = reverse_lazy("password_reset_done")
