from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from accounts.validators import validate_email_domain
from accounts.forms import SignUpForm


class EmailValidatorTest(TestCase):

    def test_my_validator(self):
        with self.assertRaises(ValidationError):
            validate_email_domain("safoijsaiof")
        self.assertIsNone(validate_email_domain("valid@nyu.edu"))


class SignUpFormTestCase(TestCase):
    def test_invalid_form(self):
        # Missing required fields
        form_data = {}
        form = SignUpForm(data=form_data)
        self.assertFalse(form.is_valid())


class SignUpViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("signup")

    def test_signup_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/signup.html")

    def test_signup_view_post_invalid_data(self):
        data = {
            "username": "",  # Empty username
            "email": "invalid_email",  # Invalid email
            "first_name": "",
            "last_name": "",
            "password": "password",
            "password2": "different_password",  # Passwords don't match
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)  # Stay on the signup page
