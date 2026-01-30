from django.test import TestCase
from tournament.models import Match, Tournament
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
        from tournament.models import Team

        self.team1 = Team.objects.create(tournament=self.tournament, name="Team 1", number=1)
        self.team2 = Team.objects.create(tournament=self.tournament, name="Team 2", number=2)
        self.team3 = Team.objects.create(tournament=self.tournament, name="Team 3", number=3)
        self.team4 = Team.objects.create(tournament=self.tournament, name="Team 4", number=4)

    def test_creates_matches_when_enabled(self):
        """Should create matches when auto_match_creation is enabled."""
        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        self.assertGreater(len(created), 0)

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

    def test_match_ordering_increments(self):
        """New matches should have correct ordering numbers."""
        # Create existing match
        Match.objects.create(tournament=self.tournament, ordering=5, status=Match.STATUSES.DONE)

        controller = get_sport_controller(self.tournament.sport)
        created = controller.create_next_matches(self.tournament)

        self.assertGreater(len(created), 0)
        self.assertEqual(created[0].ordering, 6)
