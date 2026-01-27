from django.test import TestCase
from django.urls import reverse
from user.models import User, Client, Profile
from tournament.models import Tournament


class TestDashboardViews(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="dashboard@test.com", password="password123", username="dashboard@test.com")
        # Profile is created automatically in UserController but let's ensure it exists if tested directly
        self.profile, _ = Profile.objects.get_or_create(user=self.user, pseudo="tester")
        self.client.login(email="dashboard@test.com", password="password123")

    def test_dashboard_view_access(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user/dashboard.html")

    def test_settings_view_access(self):
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "user/settings.html")

    def test_profile_update(self):
        data = {"form_name": "profile", "pseudo": "new_pseudo"}
        response = self.client.post(reverse("settings"), data)
        self.assertRedirects(response, reverse("dashboard"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.pseudo, "new_pseudo")

    def test_client_update(self):
        data = {"form_name": "client", "name": "My Corp", "address": "123 Street", "vat_number": "FR123"}
        response = self.client.post(reverse("settings"), data)
        self.assertRedirects(response, reverse("dashboard"))
        client = Client.objects.get(user=self.user)
        self.assertEqual(client.name, "My Corp")

    def test_dashboard_tournament_listing(self):
        Tournament.objects.create(name="Owned Tournament", admin=self.user, nb_teams=10)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Owned Tournament")

    def test_home_view_redirect_if_authenticated(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_logout_view(self):
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("home"))
        # Check if user is logged out (by trying to access dashboard)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)  # Redirect to login
