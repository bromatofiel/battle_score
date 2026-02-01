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


class ScoreUpdateTest(TestCase):
    """Tests for score update functionality."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", email="admin@score.test", password="password")
        self.non_admin = User.objects.create_user(username="user", email="user@score.test", password="password")
        self.tournament = Tournament.objects.create(name="Score Tournament", admin=self.admin, status=Tournament.STATUSES.ONGOING)
        from tournament.models import Team

        self.team1 = Team.objects.create(tournament=self.tournament, name="Team A", number=1)
        self.team2 = Team.objects.create(tournament=self.tournament, name="Team B", number=2)
        self.match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.ONGOING)
        self.match.teams.set([self.team1, self.team2])

    def test_admin_can_update_scores(self):
        """Admin should be able to create/update scores."""
        self.client.force_login(self.admin)

        url = reverse("tournament:score_update", kwargs={"tournament_id": self.tournament.id, "match_id": self.match.id})
        response = self.client.post(url, {f"score_{self.team1.id}": "10", f"score_{self.team2.id}": "5"})

        self.assertEqual(response.status_code, 302)
        from tournament.models import Score

        self.assertEqual(Score.objects.filter(match=self.match).count(), 2)
        self.assertEqual(Score.objects.get(match=self.match, team=self.team1).value, 10)
        self.assertEqual(Score.objects.get(match=self.match, team=self.team2).value, 5)

    def test_non_admin_cannot_update_scores(self):
        """Non-admin should get 403 when updating scores."""
        self.client.force_login(self.non_admin)

        url = reverse("tournament:score_update", kwargs={"tournament_id": self.tournament.id, "match_id": self.match.id})
        response = self.client.post(url, {f"score_{self.team1.id}": "10"})

        self.assertEqual(response.status_code, 403)

    def test_empty_score_deletes_existing(self):
        """Empty score value should delete existing score."""
        from tournament.models import Score

        Score.objects.create(match=self.match, team=self.team1, value=10)
        self.client.force_login(self.admin)

        url = reverse("tournament:score_update", kwargs={"tournament_id": self.tournament.id, "match_id": self.match.id})
        response = self.client.post(url, {f"score_{self.team1.id}": ""})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Score.objects.filter(match=self.match, team=self.team1).count(), 0)

    def test_auto_switch_to_ongoing_when_score_entered(self):
        """Match should auto-switch from COMING to ONGOING when first score is entered."""
        self.match.status = Match.STATUSES.COMING
        self.match.save()
        self.client.force_login(self.admin)

        url = reverse("tournament:score_update", kwargs={"tournament_id": self.tournament.id, "match_id": self.match.id})
        response = self.client.post(url, {f"score_{self.team1.id}": "5"})

        self.assertEqual(response.status_code, 302)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, Match.STATUSES.ONGOING)

    def test_can_change_status_via_button(self):
        """Admin should be able to change match status via button."""
        self.match.status = Match.STATUSES.COMING
        self.match.save()
        self.client.force_login(self.admin)

        url = reverse("tournament:score_update", kwargs={"tournament_id": self.tournament.id, "match_id": self.match.id})
        response = self.client.post(url, {"status": "DONE"})

        self.assertEqual(response.status_code, 302)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, Match.STATUSES.DONE)
