import json
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from accounts.validators import validate_email_domain
from accounts.forms import SignUpForm
from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from .models import UserDocument, UserReports
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

User = get_user_model()


class EmailValidatorTest(TestCase):
    def test_my_validator(self):
        with self.assertRaises(ValidationError):
            validate_email_domain("safoijsaiof")
        self.assertIsNone(validate_email_domain("valid@nyu.edu"))

    def test_invalid_form(self):
        # Missing required fields
        form_data = {}
        form = SignUpForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_send_email(self):
        # Send an email using Django's send_mail function
        mail.send_mail(
            "Test Subject",
            "Test Message",
            "routepals1@gmail.com",
            ["adsufhiu@example.com"],
            fail_silently=False,
        )

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)

        # Verify that the subject and body are correct
        self.assertEqual(mail.outbox[0].subject, "Test Subject")
        self.assertEqual(mail.outbox[0].body, "Test Message")

        # Verify that the sender and recipient are correct
        self.assertEqual(mail.outbox[0].from_email, "routepals1@gmail.com")
        self.assertEqual(mail.outbox[0].to, ["adsufhiu@example.com"])


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
        self.assertRedirects(response, reverse("home"))

        # Try to access the previous trips page
        response = self.client.get(reverse("previous_trips"))
        self.assertRedirects(response, reverse("home"))

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
        self.assertRedirects(response, reverse("home"))

        # Try to access the chat room
        response = self.client.get(reverse("chat_room", kwargs={"pk": 1}))
        self.assertRedirects(response, reverse("home"))


class SignUpViewTests(TestCase):
    def setUp(self):
        self.url = reverse("signup")  # Adjust based on your URL configuration

    @patch("accounts.views.WelcomeEmail")  # Mock the email sending function
    def test_signup_success(self, mock_welcome_email):
        response = self.client.post(
            self.url,
            {
                "username": "testuser",
                "email": "testuser@nyu.edu",
                "first_name": "test",
                "last_name": "user",
                "password1": "asdfcyugas2349",
                "password2": "asdfcyugas2349",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="testuser").exists())
        mock_welcome_email.assert_called_once()


class ChangePasswordViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="oldpassword"
        )
        self.client.login(username="testuser", password="oldpassword")
        self.url = reverse("password_change")

    def test_change_password_success(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "oldpassword",
                "new_password1": "newpassword123",
                "new_password2": "newpassword123",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))


class DocumentUploadViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        self.client.login(username="testuser", password="password123")
        self.url = reverse("upload_document")  # Adjust based on your URL configuration

    @patch("accounts.views.upload_file_to_s3")  # Mock S3 upload
    def test_upload_document_success(self, mock_upload):
        mock_upload.return_value = "http://mock-s3-url.com/base.html"

        with open("templates/base.html", "rb") as doc:
            response = self.client.post(
                self.url, {"document": doc, "fileDescription": "Test Document"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserDocument.objects.filter(filename="base.html").exists())


class DocumentDeleteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        self.client.login(username="testuser", password="password123")
        self.document = UserDocument.objects.create(
            user=self.user, filename="testfile.pdf", s3_key="mock-s3-key"
        )
        self.url = reverse("delete_document")  # Adjust based on your URL configuration

    @patch("accounts.views.delete_file_from_s3")  # Mock S3 delete
    def test_delete_document_success_1(self, mock_delete):
        self.document.delete()
        self.assertFalse(
            UserDocument.objects.filter(s3_key=self.document.s3_key).exists()
        )


class AccountViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="test123", email="test@example.com"
        )
        self.client.login(username="testuser", password="test123")

    def test_model_str_methods(self):
        """Test string representations of models"""
        # Test UserDocument str
        doc = UserDocument.objects.create(
            user=self.user, filename="test.pdf", s3_key="test-key"
        )
        self.assertEqual(str(doc), "test.pdf - testuser")

        # Test UserReports str
        reported_user = User.objects.create_user(
            username="reporteduser", password="testpass"
        )
        report = UserReports.objects.create(
            reporter=self.user,
            reported_user=reported_user,
            subject="Test",
            description="Test",
        )
        self.assertEqual(str(report), "Report by testuser on reporteduser")

    def test_non_nyu_domain(self):
        """Test that non-nyu.edu emails are rejected"""
        with self.assertRaisesMessage(ValidationError, "Invalid email domain."):
            validate_email_domain("test@gmail.com")

    def test_welcome_email(self):
        from accounts.views import WelcomeEmail

        WelcomeEmail(self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Welcome to RoutePals!")
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn(self.user.username, mail.outbox[0].body)

    @patch("accounts.views.generate_presigned_url")
    def test_upload_documents_view(self, mock_generate_url):
        mock_generate_url.return_value = "https://test-url.com"

        doc = UserDocument.objects.create(
            user=self.user, filename="test.pdf", s3_key="test-key"
        )

        response = self.client.get(reverse("user_document_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "documents/user_document_list.html")
        self.assertIn(doc, response.context["documents"])

    @patch("accounts.views.upload_file_to_s3")
    def test_upload_document_exception(self, mock_upload):
        mock_upload.side_effect = Exception("Upload failed")

        with open("templates/base.html", "rb") as file:
            response = self.client.post(
                reverse("upload_document"),
                {"document": file, "fileDescription": "test"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Upload failed")

    def test_upload_document_no_file(self):
        response = self.client.post(
            reverse("upload_document"), {"fileDescription": "test"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "No document attachment found.")

    @patch("utils.s3_utils.s3_client")
    def test_delete_document_success_2(self, mock_s3):
        # Setup mock
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.head_object.return_value = True  # Pretend file exists
        mock_s3.delete_object.return_value = True

        self.document = UserDocument.objects.create(
            user=self.user, filename="testfile.pdf", s3_key="mock-s3-key"
        )
        response = self.client.post(
            reverse("delete_document"),
            json.dumps({"document_id": self.document.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserDocument.objects.filter(id=self.document.id).exists())

    def test_delete_document_no_id(self):
        response = self.client.post(
            reverse("delete_document"), json.dumps({}), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_delete_document_not_found(self):
        response = self.client.post(
            reverse("delete_document"),
            json.dumps({"document_id": 99999}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)

    @patch("accounts.views.delete_file_from_s3")
    def test_delete_document_exception(self, mock_delete):
        doc = UserDocument.objects.create(
            user=self.user, filename="test.pdf", s3_key="test-key"
        )

        mock_delete.side_effect = Exception("Delete failed")

        response = self.client.post(
            reverse("delete_document"),
            json.dumps({"document_id": doc.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])


class LoginViewTests(TestCase):
    def setUp(self):
        # Create a test user
        self.username = "testuser"
        self.password = "testpassword"
        self.user = User.objects.create_user(
            username=self.username, password=self.password
        )

    def test_login_success(self):
        # Test successful login
        response = self.client.post(
            reverse("login"),
            {
                "username": self.username,
                "password": self.password,
            },
        )

        # Check that the user is logged in
        self.assertEqual(response.status_code, 302)  # Should redirect after login
        self.assertRedirects(response, reverse("home"))  # Redirects to home page
        self.assertTrue(
            response.wsgi_request.user.is_authenticated
        )  # User should be authenticated

    def test_login_failure(self):
        # Test unsuccessful login with invalid credentials
        response = self.client.post(
            reverse("login"),
            {
                "username": "wronguser",
                "password": "wrongpassword",
            },
        )

        # Check that the response is a 200 OK and contains the error message
        self.assertEqual(
            response.status_code, 200
        )  # Should render the login page again
        self.assertContains(
            response, "Invalid username and/or password."
        )  # Error message should be present
        self.assertFalse(
            response.wsgi_request.user.is_authenticated
        )  # User should not be authenticated

    def test_login_get(self):
        # Test GET request to the login view
        response = self.client.get(reverse("login"))

        # Check that the response is a 200 OK and contains the authentication form
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["form"], AuthenticationForm)
