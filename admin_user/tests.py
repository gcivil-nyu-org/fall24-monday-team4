import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from accounts.models import UserDocument, UserReports


class AdminUserViewsTestCase(TestCase):
    @patch("utils.s3_utils.generate_presigned_url")
    def setUp(self, mock_url):
        mock_url.return_value = "https://test-url.com"
        # Create staff user with verification
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass", is_staff=True
        )
        # Set staff user as verified immediately after creation
        self.staff_user.userprofile.is_verified = True
        self.staff_user.userprofile.save()

        # Create regular user
        self.regular_user = User.objects.create_user(
            username="regularuser", password="testpass"
        )

        self.user_profile = self.regular_user.userprofile
        self.user_profile.is_verified = False
        self.user_profile.save()

        # Create test document
        self.user_document = UserDocument.objects.create(
            user=self.regular_user,
            filename="test_doc.pdf",
            status=1,
            s3_key="test-s3-key",
        )

        # Create test report
        self.user_report = UserReports.objects.create(
            reporter=self.staff_user,
            reported_user=self.regular_user,
            subject="Test Report",
            description="Test description",
            is_acknowledged=False,
        )

        self.client = Client()

    def test_admin_view_unauthorized(self):
        self.client.login(username="regularuser", password="testpass")
        response = self.client.get(reverse("admin_view"))
        self.assertEqual(response.status_code, 302)

    def test_acknowledge_report(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("acknowledge_report"),
            data={"report_id": self.user_report.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user_report.refresh_from_db()
        self.assertTrue(self.user_report.is_acknowledged)

    @patch("admin_user.views.deactivate_account_email")
    def test_deactivate_account(self, mock_send_deactivate_account_email):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("deactivate_account"),
            data={"user_id": self.regular_user.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)
        mock_send_deactivate_account_email.assert_called_once()

    @patch("admin_user.views.activate_account_email")
    def test_activate_account(self, mock_activate_account_email):
        self.regular_user.is_active = False
        self.regular_user.save()

        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("activate_account"),
            data={"user_id": self.regular_user.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_active)
        mock_activate_account_email.assert_called_once()

    @patch("admin_user.views.verify_account_email")
    def test_verify_account(self, mock_send_verify_account_email):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("verify_account"),
            data={"user_id": self.regular_user.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertTrue(self.user_profile.is_verified)
        mock_send_verify_account_email.assert_called_once()

    @patch("admin_user.views.unverify_account_email")
    def test_unverify_account(self, mock_send_unverify_account_email):
        self.user_profile.is_verified = True
        self.user_profile.save()

        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("unverify_account"),
            data={"user_id": self.regular_user.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertFalse(self.user_profile.is_verified)
        mock_send_unverify_account_email.assert_called_once()

    def test_reported_users_list(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.get(reverse("reported_users"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("reports", response.json())
        self.assertEqual(response.json()["reports"][0]["total_report_count"], 1)

    def test_get_user_reports_invalid_user_id(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.get(reverse("get_user_reports") + "?user_id=99999")
        self.assertEqual(response.status_code, 404)

    def test_acknowledge_report_invalid_json(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("acknowledge_report"),
            data="Invalid JSON",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Invalid JSON data")


class AdminViewsBaseTest(TestCase):
    @patch("utils.s3_utils.generate_presigned_url")
    def setUp(self, mock_url):
        mock_url.return_value = "https://test-url.com"
        self.client = Client()

        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin", password="test123", is_staff=True
        )
        self.admin_user.userprofile.is_verified = True
        self.admin_user.userprofile.save()

        # Create regular user
        self.regular_user = User.objects.create_user(
            username="user", password="test123"
        )

        # Create document
        self.document = UserDocument.objects.create(
            user=self.regular_user, filename="test.pdf", s3_key="test-key", status=1
        )

        # Create report
        self.report = UserReports.objects.create(
            reporter=self.admin_user,
            reported_user=self.regular_user,
            subject="Test Report",
            description="Test",
        )

        self.client.login(username="admin", password="test123")


class AdminViewTest(AdminViewsBaseTest):
    @patch("utils.s3_utils.s3_client")
    def test_admin_view_success(self, mock_s3):
        # Setup mock
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://test-url.com"

        response = self.client.get(reverse("admin_view"))
        self.assertEqual(response.status_code, 200)

    def test_admin_view_unauthorized(self):
        self.client.login(username="user", password="test123")
        response = self.client.get(reverse("admin_view"))
        self.assertEqual(response.status_code, 302)


class DocumentManagementTest(AdminViewsBaseTest):
    @patch("utils.s3_utils.s3_client")
    def test_get_user_documents_success(self, mock_s3):
        # Setup mock
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://test-url.com"

        response = self.client.get(
            reverse("get_user_documents", kwargs={"user_id": self.regular_user.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_get_user_documents_user_not_found(self):
        response = self.client.get(
            reverse("get_user_documents", kwargs={"user_id": 99999})
        )
        self.assertEqual(response.status_code, 404)

    @patch("utils.s3_utils.s3_client")
    def test_accept_document_success(self, mock_s3):
        # Setup mock
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://test-url.com"

        response = self.client.post(
            reverse(
                "accept_document",
                kwargs={
                    "user_id": self.regular_user.id,
                    "document_id": self.document.id,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_accept_document_not_found(self):
        response = self.client.post(
            reverse(
                "accept_document",
                kwargs={"user_id": self.regular_user.id, "document_id": 99999},
            )
        )
        self.assertEqual(response.status_code, 404)

    @patch("utils.s3_utils.s3_client")
    def test_reject_document_success(self, mock_s3):
        # Setup mock
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = "https://test-url.com"

        response = self.client.post(
            reverse(
                "reject_document",
                kwargs={
                    "user_id": self.regular_user.id,
                    "document_id": self.document.id,
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_reject_document_not_found(self):
        response = self.client.post(
            reverse(
                "reject_document",
                kwargs={"user_id": self.regular_user.id, "document_id": 99999},
            )
        )
        self.assertEqual(response.status_code, 404)


class ReportManagementTest(AdminViewsBaseTest):
    def test_get_user_reports_success(self):
        response = self.client.get(
            reverse("get_user_reports"), {"user_id": self.regular_user.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("reports", response.json())

    def test_get_user_reports_user_not_found(self):
        response = self.client.get(reverse("get_user_reports"), {"user_id": 99999})
        self.assertEqual(response.status_code, 404)

    def test_acknowledge_report_json_error(self):
        response = self.client.post(
            reverse("acknowledge_report"),
            data="invalid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON data", response.json()["error"])

    def test_acknowledge_report_exception(self):
        response = self.client.post(
            reverse("acknowledge_report"),
            data=json.dumps({"report_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


class UserManagementTest(AdminViewsBaseTest):
    def test_deactivate_account_no_user_id(self):
        response = self.client.post(
            reverse("deactivate_account"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_deactivate_account_exception(self):
        response = self.client.post(
            reverse("deactivate_account"),
            data=json.dumps({"user_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_activate_account_no_user_id(self):
        response = self.client.post(
            reverse("activate_account"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_activate_account_exception(self):
        response = self.client.post(
            reverse("activate_account"),
            data=json.dumps({"user_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_verify_account_no_user_id(self):
        response = self.client.post(
            reverse("verify_account"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_verify_account_exception(self):
        response = self.client.post(
            reverse("verify_account"),
            data=json.dumps({"user_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_unverify_account_no_user_id(self):
        response = self.client.post(
            reverse("unverify_account"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unverify_account_exception(self):
        response = self.client.post(
            reverse("unverify_account"),
            data=json.dumps({"user_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_set_emergency_support_no_user_id(self):
        response = self.client.post(
            reverse("set_emergency_support"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_set_emergency_support_exception(self):
        response = self.client.post(
            reverse("set_emergency_support"),
            data=json.dumps({"user_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_set_admin_no_user_id(self):
        response = self.client.post(
            reverse("set_admin"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_set_admin_exception(self):
        response = self.client.post(
            reverse("set_admin"),
            data=json.dumps({"user_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_unset_admin_no_user_id(self):
        response = self.client.post(
            reverse("unset_admin"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unset_admin_exception(self):
        response = self.client.post(
            reverse("unset_admin"),
            data=json.dumps({"user_id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


class EmergencySupportTestCase(TestCase):
    def setUp(self):
        # Create a staff user
        self.staff_user = User.objects.create_user(
            username="staffuser", password="12345", is_staff=True
        )
        self.staff_user.userprofile.save()

        # Create a non-staff user
        self.normal_user = User.objects.create_user(
            username="normaluser", password="12345"
        )
        self.normal_user.userprofile.save()

        # Create a client
        self.client = Client()

    def test_set_emergency_support_success(self):
        self.client.login(username="staffuser", password="12345")
        response = self.client.post(
            reverse("set_emergency_support"),
            data=json.dumps({"user_id": self.normal_user.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)["success"])
        self.normal_user.userprofile.refresh_from_db()
        self.assertTrue(self.normal_user.userprofile.is_emergency_support)

    def test_unset_emergency_support_success(self):
        self.normal_user.userprofile.is_emergency_support = True
        self.normal_user.userprofile.save()
        self.client.login(username="staffuser", password="12345")
        response = self.client.post(
            reverse("unset_emergency_support"),
            data=json.dumps({"user_id": self.normal_user.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)["success"])
        self.normal_user.userprofile.refresh_from_db()
        self.assertFalse(self.normal_user.userprofile.is_emergency_support)

    def test_set_emergency_support_no_user_id(self):
        self.client.login(username="staffuser", password="12345")
        response = self.client.post(
            reverse("set_emergency_support"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(json.loads(response.content)["success"])

    def test_unset_emergency_support_no_user_id(self):
        self.client.login(username="staffuser", password="12345")
        response = self.client.post(
            reverse("unset_emergency_support"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(json.loads(response.content)["success"])

    def test_set_emergency_support_non_existent_user(self):
        self.client.login(username="staffuser", password="12345")
        response = self.client.post(
            reverse("set_emergency_support"),
            data=json.dumps({"user_id": 9999}),  # Non-existent user ID
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_unset_emergency_support_non_existent_user(self):
        self.client.login(username="staffuser", password="12345")
        response = self.client.post(
            reverse("unset_emergency_support"),
            data=json.dumps({"user_id": 9999}),  # Non-existent user ID
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)

    def test_set_emergency_support_unauthenticated(self):
        response = self.client.post(
            reverse("set_emergency_support"),
            data=json.dumps({"user_id": self.normal_user.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_unset_emergency_support_unauthenticated(self):
        response = self.client.post(
            reverse("unset_emergency_support"),
            data=json.dumps({"user_id": self.normal_user.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_set_emergency_support_non_staff(self):
        self.client.login(username="normaluser", password="12345")
        response = self.client.post(
            reverse("set_emergency_support"),
            data=json.dumps({"user_id": self.normal_user.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_unset_emergency_support_non_staff(self):
        self.client.login(username="normaluser", password="12345")
        response = self.client.post(
            reverse("unset_emergency_support"),
            data=json.dumps({"user_id": self.normal_user.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)


class SetAdminViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("set_admin")
        self.user = get_user_model().objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass123"
        )
        self.staff_user = get_user_model().objects.create_user(
            username="staffuser",
            email="staffuser@example.com",
            password="staffpass123",
            is_staff=True,
        )

    def test_set_admin_success(self):
        self.client.force_login(self.staff_user)
        data = {"user_id": self.user.id}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)

    def test_set_admin_missing_user_id(self):
        self.client.force_login(self.staff_user)
        data = {}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["error"], "User ID is required.")

    def test_set_admin_invalid_user_id(self):
        self.client.force_login(self.staff_user)
        data = {"user_id": 9999}  # Non-existent user ID
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 500)

    def test_set_admin_unauthenticated(self):
        data = {"user_id": self.user.id}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login page

    def test_set_admin_non_staff(self):
        self.client.force_login(self.user)
        data = {"user_id": self.user.id}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(
            response.status_code, 302
        )  # Redirect due to @staff_member_required

    def test_set_admin_get_method(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    # Mock test for @verification_required
    def test_set_admin_not_verified(self):
        # Assuming @verification_required checks a 'is_verified' field
        self.staff_user.is_verified = False
        self.staff_user.save()
        self.client.force_login(self.staff_user)
        data = {"user_id": self.user.id}
        response = self.client.post(
            self.url, data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)  # Forbidden


class UnsetAdminTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("unset_admin")

        # Create a superuser (admin)
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpassword"
        )

        # Create a regular staff user
        self.staff_user = get_user_model().objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="staffpassword",
            is_staff=True,
        )

        # Create a regular non-staff user
        self.regular_user = get_user_model().objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password="regularpassword",
        )

    def test_unset_admin_success(self):
        self.client.force_login(self.admin_user)
        data = {"user_id": self.staff_user.id}
        response = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.staff_user.refresh_from_db()
        self.assertFalse(self.staff_user.is_staff)

    def test_unset_admin_missing_user_id(self):
        self.client.force_login(self.admin_user)
        data = {}
        response = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "User ID is required.")

    def test_unset_admin_non_existent_user(self):
        self.client.force_login(self.admin_user)
        data = {"user_id": 9999}  # Non-existent user ID
        response = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 500)

    def test_unset_admin_unauthorized(self):
        self.client.force_login(self.regular_user)
        data = {"user_id": self.staff_user.id}
        response = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 302)  # Forbidden

    def test_unset_admin_not_logged_in(self):
        data = {"user_id": self.staff_user.id}
        response = self.client.post(
            self.url, json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 302)  # Redirect to login page

    def test_unset_admin_get_method_not_allowed(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_unset_admin_invalid_json(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            self.url, "invalid json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])
