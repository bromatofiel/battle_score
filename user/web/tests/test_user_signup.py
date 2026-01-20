from django.test import TestCase
from django.urls import reverse
from user.models import User


class TestUserSignup(TestCase):
    def test_signup_view_get(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user/signup.html")

    def test_signup_view_post_success(self):
        data = {"email": "test@example.com", "pseudo": "testuser", "password": "password123", "password_confirm": "password123"}
        response = self.client.post(reverse("signup"), data)
        self.assertRedirects(response, reverse("login"))

        user = User.objects.get(email="test@example.com")
        self.assertEqual(user.profile.pseudo, "testuser")
