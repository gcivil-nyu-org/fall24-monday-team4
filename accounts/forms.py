from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy
from .validators import NyuEmailValidator


# Form for user account sign up
class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label=gettext_lazy("Email"),
        validators=[NyuEmailValidator(allowlist=["nyu.edu"])],
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


# Form for admin creation
class AdminCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label=gettext_lazy("Email"))

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

    def save(self, commit=True):
        user = super(AdminCreationForm, self).save(commit=False)
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user
