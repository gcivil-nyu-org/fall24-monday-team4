from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch
from accounts.models import UserDocument, UserReports

class AdminUserViewsTestCase(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass", is_staff=True
        )

        self.regular_user = User.objects.create_user(
            username="regularuser", password="testpass"
        )

        self.user_profile = self.regular_user.userprofile
        self.user_profile.is_verified = False

        self.user_document = UserDocument.objects.create(
            user=self.regular_user,
            filename="test_doc.pdf",
            status=1,
            s3_key="test-s3-key",
        )

        self.user_report = UserReports.objects.create(
            reporter=self.staff_user,
            reported_user=self.regular_user,
            subject="Test Report",
            description="Test description",
            is_acknowledged=False,
        )

        self.client = Client()

    def test_admin_view_access(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.get(reverse("admin_view"))
        self.assertEqual(response.status_code, 200)

    def test_admin_view_unauthorized(self):
        self.client.login(username="regularuser", password="testpass")
        response = self.client.get(reverse("admin_view"))
        print("res: ", response)
        self.assertEqual(response.status_code, 302)

    def test_get_user_documents(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.get(
            reverse("get_user_documents", args=[self.regular_user.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("documents", data)

    def test_accept_document(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse(
                "accept_document", args=[self.regular_user.id, self.user_document.id]
            )
        )
        self.assertEqual(response.status_code, 200)
        self.user_document.refresh_from_db()
        self.assertEqual(self.user_document.status, 2)

    def test_reject_document(self):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse(
                "reject_document", args=[self.regular_user.id, self.user_document.id]
            )
        )
        self.assertEqual(response.status_code, 200)
        self.user_document.refresh_from_db()
        self.assertEqual(self.user_document.status, 3)

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

    @patch("admin_user.views.send_mail")
    def test_deactivate_account(self, mock_send_mail):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("deactivate_account"),
            data={"user_id": self.regular_user.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)
        mock_send_mail.assert_called_once()

    @patch("admin_user.views.send_mail")
    def test_activate_account(self, mock_send_mail):
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
        mock_send_mail.assert_called_once()

    @patch("admin_user.views.send_mail")
    def test_verify_account(self, mock_send_mail):
        self.client.login(username="staffuser", password="testpass")
        response = self.client.post(
            reverse("verify_account"),
            data={"user_id": self.regular_user.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertTrue(self.user_profile.is_verified)
        mock_send_mail.assert_called_once()

    @patch("admin_user.views.send_mail")
    def test_unverify_account(self, mock_send_mail):
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
        mock_send_mail.assert_called_once()

    def test_reported_users_list(self):
        response = self.client.get(reverse("reported_users"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("reports", response.json())
        self.assertEqual(response.json()["reports"][0]["total_report_count"], 1)

    def test_get_user_reports_invalid_user_id(self):
        response = self.client.get(reverse("get_user_reports") + "?user_id=99999")
        self.assertEqual(response.status_code, 404)

    def test_acknowledge_report_invalid_json(self):
        response = self.client.post(
            reverse("acknowledge_report"),
            data="Invalid JSON",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Invalid JSON data")