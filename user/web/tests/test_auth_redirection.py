from django.test import TestCase
from django.urls import reverse
from user.models import User


class TestAuthRedirection(TestCase):
    def setUp(self):
        self.email = "auth-user@test.com"
        self.password = "password123"
        self.user = User.objects.create_user(email=self.email, password=self.password, username=self.email)

    def test_login_redirect_if_authenticated(self):
        """Verify redirect to dashboard when accessing /login/ while logged in."""
        self.client.login(email=self.email, password=self.password)
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_signup_redirect_if_authenticated(self):
        """Verify redirect to dashboard when accessing /signup/ while logged in."""
        self.client.login(email=self.email, password=self.password)
        response = self.client.get(reverse("signup"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_redirect_with_next_parameter(self):
        """Verify redirect to the 'next' URL if provided."""
        self.client.login(email=self.email, password=self.password)
        next_url = reverse("settings")
        response = self.client.get(f"{reverse('login')}?next={next_url}")
        self.assertRedirects(response, next_url)

    def test_unauthenticated_can_access_auth_views(self):
        """Verify anonymous users can still access login and signup."""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirect_to_correct_login_url(self):
        """Verify unauthenticated access redirects to /login/ (not account/login/)."""
        response = self.client.get(reverse("settings"))
        # Check that it redirects to /login/
        # Django's default would be /accounts/login/ or similar
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('settings')}")
