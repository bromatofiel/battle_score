from django.test import TestCase
from django.urls import reverse
from tournament.models import Match, Tournament
from django.contrib.auth import get_user_model

User = get_user_model()


class MatchListTest(TestCase):
    """Tests for the matches list page."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", email="admin@match.test", password="password")
        self.tournament = Tournament.objects.create(name="Test Tournament", admin=self.admin, status=Tournament.STATUSES.ONGOING)

    def test_matches_list_shows_coming_matches(self):
        """Matches with COMING status should appear in the coming section."""
        self.client.force_login(self.admin)

        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.COMING)

        url = reverse("tournament:matches", kwargs={"tournament_id": self.tournament.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(match, response.context["matches_coming"])
        self.assertTrue(response.context["has_matches"])

    def test_matches_list_shows_ongoing_matches(self):
        """Matches with ONGOING status should appear in the ongoing section."""
        self.client.force_login(self.admin)

        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.ONGOING)

        url = reverse("tournament:matches", kwargs={"tournament_id": self.tournament.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(match, response.context["matches_ongoing"])

    def test_matches_list_shows_done_matches(self):
        """Matches with DONE status should appear in the done section."""
        self.client.force_login(self.admin)

        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.DONE)

        url = reverse("tournament:matches", kwargs={"tournament_id": self.tournament.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(match, response.context["matches_done"])

    def test_empty_matches_list_has_matches_false(self):
        """Empty matches list should have has_matches = False."""
        self.client.force_login(self.admin)

        url = reverse("tournament:matches", kwargs={"tournament_id": self.tournament.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["has_matches"])

    def test_matches_ordered_by_reverse_creation(self):
        """Matches should be ordered by reverse creation date within each section."""
        self.client.force_login(self.admin)

        match1 = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.COMING)
        match2 = Match.objects.create(tournament=self.tournament, ordering=2, status=Match.STATUSES.COMING)
        match3 = Match.objects.create(tournament=self.tournament, ordering=3, status=Match.STATUSES.COMING)

        url = reverse("tournament:matches", kwargs={"tournament_id": self.tournament.id})
        response = self.client.get(url)

        coming_matches = list(response.context["matches_coming"])
        # Most recently created should be first
        self.assertEqual(coming_matches[0], match3)
        self.assertEqual(coming_matches[1], match2)
        self.assertEqual(coming_matches[2], match1)
