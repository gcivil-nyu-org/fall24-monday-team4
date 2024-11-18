from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserReports
from .models import UserProfile
from django.core.files.uploadedfile import SimpleUploadedFile


class UserProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="12345", email="test@example.com"
        )

        self.user_profile = self.user.userprofile

        self.user_profile.bio = "Test bio"
        self.user_profile.is_verified = True
        self.user_profile.save()

        self.client.login(username="testuser", password="12345")

    def test_profile_view_update_bio(self):
        response = self.client.post(reverse("profile"), {"bio": "Updated test bio"})

        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.bio, "Updated test bio")
        self.assertRedirects(response, reverse("profile"))

    def test_upload_profile_picture(self, mock_delete, mock_upload):
        mock_upload.return_value = "https://test-s3-url.com"
        mock_delete.return_value = True

        test_image = SimpleUploadedFile(
            name="test_image.jpg", content=b"file_content", content_type="image/jpeg"
        )

        response = self.client.post(
            reverse("upload_user_profile_picture"), {"photo": test_image}
        )

        self.assertTrue(response.json()["success"])

        self.user_profile.refresh_from_db()
        self.assertIsNotNone(self.user_profile.photo_key)
        self.assertEqual(self.user_profile.file_name, "test_image.jpg")
        self.assertEqual(self.user_profile.file_type, "image/jpeg")

    def test_remove_profile_picture(self, mock_delete):
        self.user_profile.photo_key = "test-key"
        self.user_profile.file_name = "test.jpg"
        self.user_profile.file_type = "image/jpeg"
        self.user_profile.save()

        mock_delete.return_value = True

        response = self.client.post(reverse("remove_profile_picture"))

        self.assertTrue(response.json()["success"])

        self.user_profile.refresh_from_db()
        self.assertIsNone(self.user_profile.photo_key)
        self.assertIsNone(self.user_profile.file_name)
        self.assertIsNone(self.user_profile.file_type)

    def test_report_user(self):
        reported_user = User.objects.create_user(
            username="reporteduser", password="12345"
        )

        response = self.client.post(
            reverse("report_user"),
            {
                "subject": "Test Report",
                "description": "Test description",
                "reported_user_id": reported_user.id,
            },
        )

        self.assertTrue(response.json()["success"])
        self.assertTrue(
            UserReports.objects.filter(
                reporter=self.user, reported_user=reported_user, subject="Test Report"
            ).exists()
        )

    def test_user_profile_created_on_user_signup(self):
        user = User.objects.create_user(
            username="newuser", email="newuser@example.com", password="testpass123"
        )

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            self.fail("UserProfile was not created automatically")

        self.assertEqual(profile.user, user)
        self.assertFalse(profile.is_verified)

    def test_staff_user_profile_verified(self):
        user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )

        profile = UserProfile.objects.get(user=user)
        self.assertTrue(profile.is_verified)

    def test_existing_user_profile_save(self):
        user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="testpass123",
        )

        user.email = "newemail@example.com"
        user.save()

        try:
            profile = UserProfile.objects.get(user=user)
            profile.save()
        except Exception as e:
            self.fail(f"Error saving user profile: {e}")
