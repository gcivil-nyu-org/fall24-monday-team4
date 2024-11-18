from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy
from .validators import validate_email_domain


# Form for user account sign up
class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label=gettext_lazy("Email"),
        validators=[validate_email_domain],
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]
