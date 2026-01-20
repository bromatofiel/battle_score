from django.test import TestCase
from django.urls import reverse
from user.models import User


class TestUserDeletion(TestCase):
    def setUp(self):
        self.email = "delete-me@test.com"
        self.password = "security123"
        self.user = User.objects.create_user(email=self.email, password=self.password, username=self.email)
        self.client.login(email=self.email, password=self.password)

    def test_deletion_success_with_valid_password(self):
        """Verify 302 redirect to home, session cleared, and User object deleted."""
        response = self.client.post(reverse("settings"), {"form_name": "delete_account", "password": self.password})
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(User.objects.filter(email=self.email).exists())

        # Verify session is cleared (trying to access dashboard should redirect to login)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_deletion_failure_with_invalid_password(self):
        """Verify form error and User object still exists."""
        response = self.client.post(reverse("settings"), {"form_name": "delete_account", "password": "wrongpassword"})
        self.assertEqual(response.status_code, 200)  # Form re-rendered
        self.assertTrue(User.objects.filter(email=self.email).exists())

        # Check for error message in the form
        form = response.context["delete_form"]
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)
        self.assertIn("Mot de passe incorrect.", form.errors["password"])

    def test_deletion_unauthenticated_access(self):
        """Verify redirect to login."""
        self.client.logout()
        response = self.client.post(reverse("settings"), {"form_name": "delete_account", "password": self.password})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
