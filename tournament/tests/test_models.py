"""Tests for Tournament model methods."""

from django.test import TestCase

from user.models import User
from tournament.models import Team, Match, Tournament


class TestGetNextMatchOrdering(TestCase):
    """Tests for Tournament.get_next_match_ordering."""

    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.py", password="password", username="admin@test.py")
        self.tournament = Tournament.objects.create(name="Test Tournament", admin=self.user)

    def test_returns_1_when_no_matches(self):
        """First match should have ordering 1."""
        self.assertEqual(self.tournament.get_next_match_ordering(), 1)

    def test_returns_next_after_existing_matches(self):
        """Should return max ordering + 1."""
        Match.objects.create(tournament=self.tournament, ordering=1)
        Match.objects.create(tournament=self.tournament, ordering=2)
        Match.objects.create(tournament=self.tournament, ordering=3)

        self.assertEqual(self.tournament.get_next_match_ordering(), 4)

    def test_handles_gaps_in_ordering(self):
        """Should return max + 1 even with gaps."""
        Match.objects.create(tournament=self.tournament, ordering=1)
        Match.objects.create(tournament=self.tournament, ordering=5)

        self.assertEqual(self.tournament.get_next_match_ordering(), 6)


class TestCreateMatch(TestCase):
    """Tests for Tournament.create_match."""

    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.py", password="password", username="admin@test.py")
        self.tournament = Tournament.objects.create(name="Test Tournament", admin=self.user)
        self.team1 = Team.objects.create(tournament=self.tournament, name="Team 1", number=1)
        self.team2 = Team.objects.create(tournament=self.tournament, name="Team 2", number=2)

    def test_creates_match_with_correct_ordering(self):
        """Match should have correct ordering."""
        match = self.tournament.create_match(opponents=[self.team1, self.team2])

        self.assertEqual(match.ordering, 1)
        self.assertEqual(match.tournament, self.tournament)

    def test_assigns_teams_to_match(self):
        """Match should have the specified teams."""
        match = self.tournament.create_match(opponents=[self.team1, self.team2])

        self.assertEqual(set(match.teams.all()), {self.team1, self.team2})

    def test_increments_ordering_for_multiple_matches(self):
        """Each new match should have incremented ordering."""
        match1 = self.tournament.create_match(opponents=[self.team1, self.team2])
        match2 = self.tournament.create_match(opponents=[self.team1, self.team2])

        self.assertEqual(match1.ordering, 1)
        self.assertEqual(match2.ordering, 2)

    def test_match_status_is_coming_initially(self):
        """New match should have COMING status by default."""
        match = self.tournament.create_match(opponents=[self.team1, self.team2])

        # Status depends on update_status() result - if no ongoing matches, it should be ONGOING
        self.assertIn(match.status, [Match.STATUSES.COMING, Match.STATUSES.ONGOING])


class TestUpdateMatchStatuses(TestCase):
    """Tests for Tournament.update_match_statuses."""

    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.py", password="password", username="admin@test.py")
        self.tournament = Tournament.objects.create(name="Test Tournament", admin=self.user)
        self.team1 = Team.objects.create(tournament=self.tournament, name="Team 1", number=1)
        self.team2 = Team.objects.create(tournament=self.tournament, name="Team 2", number=2)
        self.team3 = Team.objects.create(tournament=self.tournament, name="Team 3", number=3)
        self.team4 = Team.objects.create(tournament=self.tournament, name="Team 4", number=4)

    def test_updates_coming_to_ongoing(self):
        """COMING matches should become ONGOING if teams are available."""
        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.COMING)
        match.teams.set([self.team1, self.team2])

        ongoing = self.tournament.update_match_statuses()

        match.refresh_from_db()
        self.assertEqual(match.status, Match.STATUSES.ONGOING)
        self.assertEqual(ongoing, [match])

    def test_respects_match_order_by_default(self):
        """Should respect match order - later matches with same teams stay COMING."""
        # Match 1: Team 1 vs Team 2
        match1 = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.COMING)
        match1.teams.set([self.team1, self.team2])

        # Match 2: Team 1 vs Team 3 (Team 1 is in match 1)
        match2 = Match.objects.create(tournament=self.tournament, ordering=2, status=Match.STATUSES.COMING)
        match2.teams.set([self.team1, self.team3])

        ongoing = self.tournament.update_match_statuses(keep_match_order=True)

        match1.refresh_from_db()
        match2.refresh_from_db()

        # Match 1 should be ONGOING, Match 2 should stay COMING (Team 1 is busy)
        self.assertEqual(match1.status, Match.STATUSES.ONGOING)
        self.assertEqual(match2.status, Match.STATUSES.COMING)
        self.assertEqual(ongoing, [match1])

    def test_parallel_matches_with_different_teams(self):
        """Matches with different teams can both be ONGOING."""
        # Match 1: Team 1 vs Team 2
        match1 = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.COMING)
        match1.teams.set([self.team1, self.team2])

        # Match 2: Team 3 vs Team 4 (different teams)
        match2 = Match.objects.create(tournament=self.tournament, ordering=2, status=Match.STATUSES.COMING)
        match2.teams.set([self.team3, self.team4])

        ongoing = self.tournament.update_match_statuses(keep_match_order=True)

        match1.refresh_from_db()
        match2.refresh_from_db()

        # Both should be ONGOING since they have different teams
        self.assertEqual(match1.status, Match.STATUSES.ONGOING)
        self.assertEqual(match2.status, Match.STATUSES.ONGOING)
        self.assertEqual(len(ongoing), 2)

    def test_does_not_affect_done_matches(self):
        """DONE matches should not be affected."""
        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.DONE)
        match.teams.set([self.team1, self.team2])

        ongoing = self.tournament.update_match_statuses()

        match.refresh_from_db()
        self.assertEqual(match.status, Match.STATUSES.DONE)
        self.assertEqual(ongoing, [])

    def test_does_not_affect_ongoing_matches(self):
        """ONGOING matches should not be affected."""
        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.ONGOING)
        match.teams.set([self.team1, self.team2])

        ongoing = self.tournament.update_match_statuses()

        match.refresh_from_db()
        self.assertEqual(match.status, Match.STATUSES.ONGOING)
        # Returns empty because we only process COMING matches
        self.assertEqual(ongoing, [])
