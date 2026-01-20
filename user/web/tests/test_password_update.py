from django.test import TestCase
from django.urls import reverse
from user.models import User


class TestUserPasswordUpdate(TestCase):
    def setUp(self):
        self.email = "pass-user@test.com"
        self.old_password = "oldpassword123"
        self.new_password = "newpassword456"
        self.user = User.objects.create_user(email=self.email, password=self.old_password, username=self.email)
        self.client.login(email=self.email, password=self.old_password)

    def test_password_update_success(self):
        """Verify successful password update redirects to login and logouts user."""
        response = self.client.post(
            reverse("settings"),
            {"form_name": "password", "old_password": self.old_password, "new_password": self.new_password, "confirm_password": self.new_password},
        )
        self.assertRedirects(response, reverse("login"))

        # Verify user is logged out
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Verify new password works
        login_success = self.client.login(email=self.email, password=self.new_password)
        self.assertTrue(login_success)

    def test_password_update_wrong_old_password(self):
        """Verify error when old password is incorrect."""
        response = self.client.post(
            reverse("settings"),
            {"form_name": "password", "old_password": "wrongpassword", "new_password": self.new_password, "confirm_password": self.new_password},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["password_form"]
        self.assertIn("old_password", form.errors)
        self.assertIn("Ancien mot de passe incorrect.", form.errors["old_password"])

    def test_password_update_mismatch(self):
        """Verify error when new passwords do not match."""
        response = self.client.post(
            reverse("settings"),
            {"form_name": "password", "old_password": self.old_password, "new_password": self.new_password, "confirm_password": "mismatchpassword"},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["password_form"]
        self.assertIn("__all__", form.errors)
        self.assertIn("Les deux mots de passe ne correspondent pas.", form.errors["__all__"])
