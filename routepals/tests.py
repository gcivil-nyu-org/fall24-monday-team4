# In routepals/tests.py (create new file)
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        # Set user as verified and emergency support
        self.user.userprofile.is_verified = True
        self.user.userprofile.is_emergency_support = True
        self.user.userprofile.save()

    def test_emergency_support_redirect(self):
        """Test that verified emergency support users are redirected"""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("emergency_support"))
