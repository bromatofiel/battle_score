from django.test import TestCase
from django.urls import reverse
from tournament.models import Team, Tournament
from django.contrib.auth import get_user_model

User = get_user_model()


class TeamDeletionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", email="admin@test.com", password="password")
        self.non_admin = User.objects.create_user(username="nonadmin", email="nonadmin@test.com", password="password")
        self.tournament = Tournament.objects.create(name="Test Tournament", admin=self.admin)
        self.team = Team.objects.create(tournament=self.tournament, name="Test Team", number=1)

    def test_admin_can_delete_team(self):
        """Admin should be able to delete a team via POST request."""
        # Force login instead of using credentials
        self.client.force_login(self.admin)

        url = reverse("tournament:team_delete", kwargs={"tournament_id": self.tournament.id, "team_id": self.team.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)  # Expect redirect to teams page
        self.assertFalse(Team.objects.filter(id=self.team.id).exists())

    def test_non_admin_cannot_delete_team(self):
        """Non-admin users should get 403 when trying to delete team."""
        self.client.force_login(self.non_admin)

        url = reverse("tournament:team_delete", kwargs={"tournament_id": self.tournament.id, "team_id": self.team.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Team.objects.filter(id=self.team.id).exists())

    def test_team_renumbering_after_deletion(self):
        """Teams should be renumbered after deletion to close gaps."""
        self.client.force_login(self.admin)

        team2 = Team.objects.create(tournament=self.tournament, name="Team 2", number=2)
        team3 = Team.objects.create(tournament=self.tournament, name="Team 3", number=3)

        url = reverse("tournament:team_delete", kwargs={"tournament_id": self.tournament.id, "team_id": self.team.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Team.objects.filter(id=self.team.id).exists())

        team2.refresh_from_db()
        team3.refresh_from_db()
        self.assertEqual(team2.number, 1)
        self.assertEqual(team3.number, 2)


class TeamCreationTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", email="admin@create.com", password="password")
        self.tournament = Tournament.objects.create(name="Test Tournament", admin=self.admin)
        self.client.force_login(self.admin)

    def test_create_single_team(self):
        """Creating a single team should work."""
        url = reverse("tournament:team_create", kwargs={"tournament_id": self.tournament.id})
        response = self.client.post(url, {"count": "1"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.tournament.teams.count(), 1)

    def test_create_multiple_teams(self):
        """Creating multiple teams at once should work."""
        url = reverse("tournament:team_create", kwargs={"tournament_id": self.tournament.id})
        response = self.client.post(url, {"count": "3"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.tournament.teams.count(), 3)
        # Check they are numbered correctly
        numbers = list(self.tournament.teams.order_by("number").values_list("number", flat=True))
        self.assertEqual(numbers, [1, 2, 3])
