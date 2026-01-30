from django.test import TestCase
from tournament.models import Team, Match, Tournament
from django.contrib.auth import get_user_model
from tournament.controllers import get_sport_controller

User = get_user_model()


class AutoMatchCreationTest(TestCase):
    """Tests for the automatic match creation algorithm."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", email="admin@auto.test", password="password")
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            admin=self.admin,
            status=Tournament.STATUSES.ONGOING,
            auto_match_creation=True,
            nb_team_matches=3,
        )
        # Create teams
        self.team1 = Team.objects.create(tournament=self.tournament, name="Team 1", number=1)
        self.team2 = Team.objects.create(tournament=self.tournament, name="Team 2", number=2)
        self.team3 = Team.objects.create(tournament=self.tournament, name="Team 3", number=3)
        self.team4 = Team.objects.create(tournament=self.tournament, name="Team 4", number=4)

    def test_creates_matches_for_all_available_teams(self):
        """Should create matches pairing all available teams."""
        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        # With 4 teams, should create 2 matches (pairing each team once)
        self.assertEqual(len(created), 2)

        # All 4 teams should be in matches
        teams_in_matches = set()
        for match in created:
            for team in match.teams.all():
                teams_in_matches.add(team.id)
        self.assertEqual(len(teams_in_matches), 4)

    def test_does_not_create_if_auto_disabled(self):
        """Should not create matches if auto_match_creation is False."""
        self.tournament.auto_match_creation = False
        self.tournament.save()

        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        self.assertEqual(len(created), 0)

    def test_does_not_create_if_no_nb_team_matches(self):
        """Should not create matches if nb_team_matches is not set."""
        self.tournament.nb_team_matches = None
        self.tournament.save()

        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        self.assertEqual(len(created), 0)

    def test_excludes_teams_with_pending_matches(self):
        """Teams with COMING or ONGOING matches should not be paired."""
        # Create a pending match for team1 and team2
        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.COMING)
        match.teams.set([self.team1, self.team2])

        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        # Only team3 and team4 available, should create 1 match
        self.assertEqual(len(created), 1)
        teams_in_new_match = set(created[0].teams.values_list("id", flat=True))
        self.assertEqual(teams_in_new_match, {self.team3.id, self.team4.id})

    def test_excludes_teams_at_match_limit(self):
        """Teams that reached nb_team_matches should not be paired."""
        self.tournament.nb_team_matches = 1
        self.tournament.save()

        # Create a completed match for team1 and team2
        match = Match.objects.create(tournament=self.tournament, ordering=1, status=Match.STATUSES.DONE)
        match.teams.set([self.team1, self.team2])

        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        # Only team3 and team4 available (they have 0 matches)
        self.assertEqual(len(created), 1)
        teams_in_new_match = set(created[0].teams.values_list("id", flat=True))
        self.assertEqual(teams_in_new_match, {self.team3.id, self.team4.id})

    def test_match_ordering_increments(self):
        """New matches should have correct ordering numbers."""
        # Create existing match
        Match.objects.create(tournament=self.tournament, ordering=5, status=Match.STATUSES.DONE)

        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        self.assertGreater(len(created), 0)
        self.assertEqual(created[0].ordering, 6)
        if len(created) > 1:
            self.assertEqual(created[1].ordering, 7)
