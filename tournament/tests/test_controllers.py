from django.test import TestCase

from user.models import User
from tournament.models import Team, Match, Score, Tournament
from tournament.controllers import get_sport_controller


class TestRankingCalculations(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.py", password="password", username="admin@test.py")
        self.tournament = Tournament.objects.create(
            name="Test Tournament", admin=self.user, sport=Tournament.SPORTS.GENERIC
        )
        self.team1 = Team.objects.create(tournament=self.tournament, name="Team 1", number=1)
        self.team2 = Team.objects.create(tournament=self.tournament, name="Team 2", number=2)
        self.team3 = Team.objects.create(tournament=self.tournament, name="Team 3", number=3)

    def test_generic_ranking_victory(self):
        # Match 1: Team 1 vs Team 2 -> Team 1 wins
        match1 = Match.objects.create(tournament=self.tournament, ordering=1)
        match1.teams.add(self.team1, self.team2)
        Score.objects.create(match=match1, team=self.team1, value=10)
        Score.objects.create(match=match1, team=self.team2, value=5)

        controller = get_sport_controller(Tournament.SPORTS.GENERIC)
        rankings = controller.get_team_scores(self.tournament)

        # Team 1 should have 1 point, Team 2 should have 0
        ranking_map = {r["team"].id: r["total_points"] for r in rankings}
        self.assertEqual(ranking_map[self.team1.id], 1)
        self.assertEqual(ranking_map[self.team2.id], 0)
        self.assertEqual(ranking_map[self.team3.id], 0)

    def test_generic_ranking_draw(self):
        # Match 1: Team 1 vs Team 2 -> Draw
        match1 = Match.objects.create(tournament=self.tournament, ordering=1)
        match1.teams.add(self.team1, self.team2)
        Score.objects.create(match=match1, team=self.team1, value=10)
        Score.objects.create(match=match1, team=self.team2, value=10)

        controller = get_sport_controller(Tournament.SPORTS.GENERIC)
        rankings = controller.get_team_scores(self.tournament)

        # Both should have 1 point
        ranking_map = {r["team"].id: r["total_points"] for r in rankings}
        self.assertEqual(ranking_map[self.team1.id], 1)
        self.assertEqual(ranking_map[self.team2.id], 1)

    def test_complex_ranking_sorting(self):
        # T1 wins vs T2 (T1:1, T2:0)
        m1 = Match.objects.create(tournament=self.tournament, ordering=1)
        Score.objects.create(match=m1, team=self.team1, value=10)
        Score.objects.create(match=m1, team=self.team2, value=0)

        # T2 draws vs T3 (T2:1, T3:1)
        m2 = Match.objects.create(tournament=self.tournament, ordering=2)
        Score.objects.create(match=m2, team=self.team2, value=5)
        Score.objects.create(match=m2, team=self.team3, value=5)

        # T3 wins vs T1 (T3:1, T1:0)
        m3 = Match.objects.create(tournament=self.tournament, ordering=3)
        Score.objects.create(match=m3, team=self.team3, value=10)
        Score.objects.create(match=m3, team=self.team1, value=0)

        # Total Expected:
        # T1: 1
        # T2: 1
        # T3: 2

        controller = get_sport_controller(Tournament.SPORTS.GENERIC)
        rankings = controller.get_team_scores(self.tournament)

        self.assertEqual(rankings[0]["team"], self.team3)
        self.assertEqual(rankings[0]["total_points"], 2)

        # T1 and T2 have 1 point, order between them can vary but they follow T3
        points = [r["total_points"] for r in rankings]
        self.assertEqual(points, [2, 1, 1])

    def test_empty_tournament(self):
        controller = get_sport_controller(Tournament.SPORTS.GENERIC)
        rankings = controller.get_team_scores(self.tournament)
        self.assertEqual(len(rankings), 3)
        for r in rankings:
            self.assertEqual(r["total_points"], 0)
            self.assertEqual(r["rank"], 1)  # All tied at 1st

    def test_generic_ranking_multi_tie(self):
        # T1 wins vs T2 (T1:1, T2:0)
        m1 = Match.objects.create(tournament=self.tournament, ordering=1)
        Score.objects.create(match=m1, team=self.team1, value=10)
        Score.objects.create(match=m1, team=self.team2, value=0)

        # T3 wins (against nobody in particular, just to get a point)
        m2 = Match.objects.create(tournament=self.tournament, ordering=2)
        Score.objects.create(match=m2, team=self.team3, value=10)
        Score.objects.create(match=m2, team=self.team2, value=0)

        # Result: T1: 1, T2: 3, T3: 1
        # T1 and T3 should be rank 1, T2 should be rank 3

        controller = get_sport_controller(Tournament.SPORTS.GENERIC)
        rankings = controller.get_team_scores(self.tournament)

        ranking_map = {r["team"].id: r["rank"] for r in rankings}
        self.assertEqual(ranking_map[self.team1.id], 1)
        self.assertEqual(ranking_map[self.team3.id], 1)
        self.assertEqual(ranking_map[self.team2.id], 3)


class TestCreateNextMatches(TestCase):
    """Tests for BaseSportController.create_next_matches."""

    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.py", password="password", username="admin@test.py")
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            admin=self.user,
            sport=Tournament.SPORTS.GENERIC,
            status=Tournament.STATUSES.ONGOING,
        )
        self.team1 = Team.objects.create(tournament=self.tournament, name="Team 1", number=1)
        self.team2 = Team.objects.create(tournament=self.tournament, name="Team 2", number=2)
        self.team3 = Team.objects.create(tournament=self.tournament, name="Team 3", number=3)
        self.controller = get_sport_controller(Tournament.SPORTS.GENERIC)

    def test_no_matches_created_if_auto_disabled(self):
        """No matches should be created if auto_match_creation is False."""
        self.tournament.auto_match_creation = False
        self.tournament.nb_team_matches = 3
        self.tournament.save()

        created = self.controller.create_next_matches(self.tournament)
        self.assertEqual(created, [])

    def test_no_matches_created_if_nb_team_matches_not_set(self):
        """No matches should be created if nb_team_matches is not set."""
        self.tournament.auto_match_creation = True
        self.tournament.nb_team_matches = None
        self.tournament.save()

        created = self.controller.create_next_matches(self.tournament)
        self.assertEqual(created, [])

    def test_creates_matches_when_enabled(self):
        """Matches should be created when auto generation is enabled."""
        self.tournament.auto_match_creation = True
        self.tournament.nb_team_matches = 2
        self.tournament.save()

        created = self.controller.create_next_matches(self.tournament)
        self.assertGreater(len(created), 0)
        self.assertEqual(Match.objects.filter(tournament=self.tournament).count(), len(created))

    def test_respects_nb_team_matches_limit(self):
        """Should not create more matches than nb_team_matches per team."""
        self.tournament.auto_match_creation = True
        self.tournament.nb_team_matches = 1
        self.tournament.save()

        # First, create initial matches
        created = self.controller.create_next_matches(self.tournament, update_match_statuses=False)

        # Mark all as done
        for match in created:
            match.status = Match.STATUSES.DONE
            match.save()

        # Try to create more matches - should not create any since each team has 1 match
        more_created = self.controller.create_next_matches(self.tournament)
        self.assertEqual(more_created, [])

    def test_does_not_create_matches_for_busy_teams(self):
        """Teams with pending matches should not get new matches."""
        self.tournament.auto_match_creation = True
        self.tournament.nb_team_matches = 3
        self.tournament.save()

        # Create first batch of matches
        created = self.controller.create_next_matches(self.tournament, update_match_statuses=False)

        # All teams should now have pending matches, so no new matches should be created
        more_created = self.controller.create_next_matches(self.tournament)
        self.assertEqual(more_created, [])
