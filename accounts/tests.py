from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from accounts.validators import validate_email_domain
from accounts.forms import SignUpForm
from django.contrib.auth.models import User


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
            "username": "",
            "email": "invalid_email",
            "first_name": "",
            "last_name": "",
            "password": "password",
            "password2": "different_password",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)


class UnverifiedUserTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="unverified_user", password="testpass"
        )
        self.user.userprofile.is_verified = False
        self.user.userprofile.save()

    def test_unverified_user_access_1(self):
        self.client.login(username="unverified_user", password="testpass")

        # Try to access the current trip page
        response = self.client.get(reverse("current_trip"))
        self.assertRedirects(response, reverse("user_document_list"))

        # Try to access the previous trips page
        response = self.client.get(reverse("previous_trips"))
        self.assertRedirects(response, reverse("user_document_list"))

        # Try to create a new trip
        response = self.client.post(
            reverse("create_trip"),
            {
                "planned_departure": "2024-06-01T12:00",
                "start_latitude": "40.7128",
                "start_longitude": "-74.0060",
                "dest_latitude": "40.7580",
                "dest_longitude": "-73.9855",
                "desired_companions": 1,
                "search_radius": 200,
            },
        )
        self.assertRedirects(response, reverse("user_document_list"))

        # Try to access the chat room
        response = self.client.get(reverse("chat_room", kwargs={"pk": 1}))
        self.assertRedirects(response, reverse("user_document_list"))
