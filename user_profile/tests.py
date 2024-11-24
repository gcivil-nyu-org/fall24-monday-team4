from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserDocument, UserReports
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from .models import UserProfile
from unittest.mock import call, patch, MagicMock
from botocore.exceptions import ClientError


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

    def test_profile_str_method(self):
        expected_str = "Profile for testuser (test@example.com)"
        self.assertEqual(str(self.user_profile), expected_str)

    @patch("user_profile.models.generate_presigned_url")
    def test_get_photo_url_with_key(self, mock_generate_url):
        mock_generate_url.return_value = "https://test-url.com/photo.jpg"
        self.user_profile.photo_key = "test-key"
        self.user_profile.save()

        url = self.user_profile.get_photo_url()
        self.assertEqual(url, "https://test-url.com/photo.jpg")
        mock_generate_url.assert_called_once_with("test-key")

    def test_get_photo_url_without_key(self):
        self.user_profile.photo_key = None
        self.user_profile.save()

        url = self.user_profile.get_photo_url()
        self.assertIsNone(url)

    def test_profile_view_update_bio(self):
        response = self.client.post(reverse("profile"), {"bio": "Updated test bio"})

        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.bio, "Updated test bio")
        self.assertRedirects(response, reverse("profile"))

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

    def test_staff_user_profile_verified(self):
        user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )

        profile = UserProfile.objects.get(user=user)
        self.assertTrue(profile.is_verified)


class EmergencySupportDecoratorTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create regular user
        self.regular_user = User.objects.create_user(
            username="regular", password="test123"
        )
        self.regular_user.userprofile.is_verified = True
        self.regular_user.userprofile.save()

        # Create emergency support user
        self.support_user = User.objects.create_user(
            username="support", password="test123"
        )
        self.support_user.userprofile.is_verified = True
        self.support_user.userprofile.is_emergency_support = True
        self.support_user.userprofile.save()

    def test_emergency_support_access(self):
        self.client.login(username="support", password="test123")
        response = self.client.get(reverse("emergency_support"))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirect(self):
        self.client.login(username="regular", password="test123")
        response = self.client.get(reverse("emergency_support"))
        self.assertRedirects(response, reverse("home"))


class UserProfileSignalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="12345", email="test@example.com"
        )
        self.user_profile = self.user.userprofile
        self.user_profile.bio = "Test bio"
        self.user_profile.is_verified = True
        self.user_profile.photo_key = "test_photo_key"
        self.user_profile.save()

        # Create test document
        self.document = UserDocument.objects.create(
            user=self.user,
            filename="test.pdf",
            s3_key="test_doc_key",
            file_type="application/pdf",
        )

    @patch("user_profile.signals.delete_file_from_s3")
    def test_delete_user_files(self, mock_delete_file):
        # Delete user which should trigger the signal
        self.user.delete()

        # Verify both profile photo and document were attempted to be deleted
        mock_delete_file.assert_any_call("test_photo_key")
        mock_delete_file.assert_any_call("test_doc_key")
        self.assertEqual(mock_delete_file.call_count, 2)

        # Verify UserDocument was deleted
        self.assertEqual(UserDocument.objects.filter(user=self.user).count(), 0)

    @patch("user_profile.signals.delete_file_from_s3")
    def test_delete_user_files_without_photo(self, mock_delete_file):
        self.user_profile.photo_key = None
        self.user_profile.save()

        self.user.delete()

        # Verify only document deletion was attempted
        mock_delete_file.assert_called_once_with("test_doc_key")

    @patch("user_profile.signals.delete_file_from_s3")
    @patch("user_profile.signals.logger")
    def test_delete_user_files_error_handling(self, mock_logger, mock_delete_file):
        mock_delete_file.side_effect = Exception("Test error")

        self.user.delete()

        # Verify error was logged
        mock_logger.error.assert_called_once_with(
            "Error deleting user files: Test error"
        )


class UserProfileViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="12345", email="test@example.com"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", password="12345", email="other@example.com"
        )

        self.user_profile = self.user.userprofile
        self.user_profile.is_verified = True
        self.user_profile.photo_key = "test_photo_key"
        self.user_profile.save()

        self.client.login(username="testuser", password="12345")

    @patch("utils.s3_utils.s3_client")
    def test_upload_profile_picture_exception_1(self, mock_s3):
        """Test exception handling in upload_profile_picture"""
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.upload_fileobj.side_effect = Exception("Upload failed")

        image_content = b"GIF89a\x01\x00\x01\x00\x00\xff\x00,\
            \x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;"
        test_image = SimpleUploadedFile(
            name="test.gif", content=image_content, content_type="image/gif"
        )

        response = self.client.post(
            reverse("upload_profile_picture"), {"photo": test_image}, format="multipart"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Upload failed")

    @patch("user_profile.views.get_object_or_404")
    def test_upload_profile_picture_exception_2(self, mock_get_object):
        # Make get_object_or_404 raise Http404
        mock_get_object.side_effect = Http404("Profile not found")

        image = SimpleUploadedFile(
            "test.jpg", b"test content", content_type="image/jpeg"
        )

        response = self.client.post(reverse("upload_profile_picture"), {"photo": image})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Profile not found")

    @patch("utils.s3_utils.s3_client")
    def test_remove_profile_picture_delete_fail(self, mock_s3):
        """Test failed deletion message in remove_profile_picture"""
        # Setup profile with photo
        self.user_profile.photo_key = "test_key"
        self.user_profile.save()

        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        # Make delete operation fail
        mock_s3.head_object.return_value = True
        mock_s3.delete_object.side_effect = Exception("Delete failed")

        response = self.client.post(reverse("remove_profile_picture"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error_message"], "Delete failed")

    def test_profile_view_without_photo(self):
        self.user_profile.photo_key = None
        self.user_profile.save()

        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["profile_picture_url"])

    @patch("utils.s3_utils.s3_client")
    def test_upload_profile_picture_success(self, mock_s3):
        # Setup mock
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.upload_fileobj.return_value = None  # S3 upload doesn't return anything
        mock_s3.generate_presigned_url.return_value = "https://test-url.com/image.jpg"

        # Create a simple test image file
        image_content = b"GIF89a\x01\x00\x01\x00\x00\xff\x00,\
            \x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;"
        test_image = SimpleUploadedFile(
            name="test.gif", content=image_content, content_type="image/gif"
        )

        response = self.client.post(
            reverse("upload_profile_picture"), {"photo": test_image}, format="multipart"
        )

        self.assertTrue(response.json()["success"])

        # Verify mock was called
        mock_s3.upload_fileobj.assert_called_once()

    def test_upload_profile_picture_no_file(self):
        response = self.client.post(reverse("upload_profile_picture"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Photo attachment not found.")

    @patch("user_profile.views.upload_file_to_s3")
    def test_upload_profile_picture_upload_fails(self, mock_upload):
        mock_upload.return_value = None

        photo = SimpleUploadedFile(
            "test.jpg", b"file_content", content_type="image/jpeg"
        )
        response = self.client.post(reverse("upload_profile_picture"), {"photo": photo})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])

    def test_report_user_exception(self):
        response = self.client.post(
            reverse("report_user"),
            {
                "subject": "Test",
                "description": "Test",
                "reported_user_id": 99999,  # Non-existent user
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("error_message", response.json())

    @patch("user_profile.views.delete_file_from_s3")
    def test_remove_profile_picture_success(self, mock_delete):
        mock_delete.return_value = True

        response = self.client.post(reverse("remove_profile_picture"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.user_profile.refresh_from_db()
        self.assertIsNone(self.user_profile.photo_key)
        self.assertIsNone(self.user_profile.file_name)
        self.assertIsNone(self.user_profile.file_type)

    @patch("utils.s3_utils.s3_client")
    def test_remove_profile_picture_oldpicdelete(self, mock_s3):
        self.user_profile.photo_key = "test_photo_key"
        self.user_profile.save()

        mock_s3.head_object.return_value = {}
        mock_s3.delete_object.side_effect = ClientError(
            error_response={"Error": {"Code": "404", "Message": "Not Found"}},
            operation_name="DeleteObject",
        )
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError

        with patch("builtins.print") as mock_print:
            response = self.client.post(reverse("remove_profile_picture"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.user_profile.refresh_from_db()
        self.assertIsNone(self.user_profile.photo_key)
        self.assertIsNone(self.user_profile.file_name)
        self.assertIsNone(self.user_profile.file_type)

        mock_print.assert_has_calls(
            [
                call("File with key test_photo_key does not exist."),
                call("Failed to delete old profile picture with key: test_photo_key"),
            ]
        )

    def test_remove_profile_picture_no_photo(self):
        self.user_profile.photo_key = None
        self.user_profile.save()

        response = self.client.post(reverse("remove_profile_picture"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["error_message"], "No profile picture to remove."
        )
