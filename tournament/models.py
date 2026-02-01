import random

from django.db import models, transaction
from django.conf import settings
from django.db.models import Max

from core.utils import enum
from core.models import BaseModel
from core.constants import COUNTRIES


class Tournament(BaseModel):
    """
    A tournament with settings.
    """

    SPORTS = enum(
        PETANQUE=("PETANQUE", "Pétanque"),
        GENERIC=("GENERIC", "Générique"),
    )

    STATUSES = enum(
        DRAFT=("DRAFT", "Brouillon"),
        PUBLISHED=("PUBLISHED", "Publié"),
        ONGOING=("ONGOING", "En cours"),
        FINISHED=("FINISHED", "Terminé"),
    )

    auto_match_creation = models.BooleanField(default=False)
    nb_team_matches = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max matches per team for auto-creation"
    )
    name = models.CharField(max_length=255)
    sport = models.CharField(max_length=20, choices=SPORTS, default=SPORTS.GENERIC)
    description = models.TextField(blank=True)
    nb_teams = models.PositiveIntegerField(default=5)
    nb_players_per_team = models.PositiveIntegerField(default=4)
    location = models.CharField(max_length=255, blank=True)
    date_start = models.DateTimeField(null=True, blank=True)
    date_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUSES.DRAFT)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="managed_tournaments")

    def __str__(self):
        return self.name

    def get_next_match_ordering(self):
        last_match = self.matches.aggregate(Max("ordering"))["ordering__max"]
        return (last_match + 1) if last_match else 1

    def create_match(self, opponents):
        """
        Create a match between specified opponents while ensuring that the tournament is locked.
        """
        with transaction.atomic():
            # Lock the tournament row to prevent race conditions
            _lock = Tournament.objects.select_for_update().get(pk=self.pk)
            next_ordering = self.get_next_match_ordering()
            new_match = Match.objects.create(tournament=self, ordering=next_ordering, status=Match.STATUSES.COMING)
            new_match.teams.set(opponents)
        new_match.update_status(save=True)
        return new_match

    def update_match_statuses(self, keep_match_order: bool = True):
        """
        Updates the statuses of matches in the tournament.
        """
        matches = self.matches.prefetch_related("teams").filter(status=Match.STATUSES.COMING)
        excluded_teams = set()
        ongoing_matches = []
        for match in matches:
            if keep_match_order:
                if any(t.id in excluded_teams for t in match.teams.all()):
                    # Skipping teams already required by previous matches
                    continue
                excluded_teams.update(t.id for t in match.teams.all())
            match.update_status(save=True)
            if match.status == Match.STATUSES.ONGOING:
                ongoing_matches.append(match)
        return ongoing_matches


class Team(BaseModel):
    """
    A group of participants linked to a tournament.
    """

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=255)
    number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.tournament.name})"

    @classmethod
    def generate_team_names(cls, tournament: Tournament, nb_new_teams: int):
        current_names = tournament.teams.values_list("name", flat=True)
        nb_current_teams = len(current_names)
        current_names = set(current_names)  # Improve performance
        available_names = [country for country, capital in COUNTRIES if country not in current_names]
        random.shuffle(available_names)
        names = []
        for i in range(nb_new_teams):
            name = available_names.pop() if available_names else f"Equipe {i + nb_current_teams}"
            names.append(name)
        return names


class Participant(BaseModel):
    """
    A user participating in a tournament with a role.
    """

    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("PLAYER", "Player"),
        ("SPECTATOR", "Spectator"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participations")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="participants")
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="members")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="PLAYER")

    class Meta:
        unique_together = ("user", "tournament")

    def __str__(self):
        return f"{self.user} in {self.tournament.name} [{self.role}]"


class Match(BaseModel):
    """
    A match between two teams.
    """

    STATUSES = enum(
        COMING=("COMING", "À venir"),
        ONGOING=("ONGOING", "En cours"),
        DONE=("DONE", "Terminé"),
    )
    STATUSES_PENDING = [STATUSES.COMING, STATUSES.ONGOING]

    date_end = models.DateTimeField(null=True, blank=True)
    date_start = models.DateTimeField(null=True, blank=True)
    details = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    ordering = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUSES.COMING)
    teams = models.ManyToManyField(Team, related_name="matches")
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="matches")

    class Meta:
        ordering = ["ordering"]

    def __str__(self):
        return f"{self.tournament.name}#{self.ordering}"

    def update_status(self, opponents: list[Team] = None, save=False):
        if opponents is None:
            # Cache optimisation (optional)
            opponents = self.teams.all()
        teams_ongoing = set(
            Team.objects.filter(tournament=self.tournament, matches__status=Match.STATUSES.ONGOING).values_list(
                "id", flat=True
            )
        )
        all_available = all(t.id not in teams_ongoing for t in opponents)
        next_status = Match.STATUSES.ONGOING if all_available else Match.STATUSES.COMING
        if save and self.status != next_status:
            self.status = next_status
            self.save(update_fields=["status"])
        return next_status


class Score(BaseModel):
    """
    A score linked to a match for a specific team.
    """

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="scores")
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    value = models.IntegerField(default=0)

    class Meta:
        unique_together = ("match", "team")

    @property
    def is_winner(self):
        """Returns True if this score is the highest in the match (no ties)."""
        other_scores = self.match.scores.exclude(pk=self.pk)
        if not other_scores.exists():
            return False
        max_other = max(s.value for s in other_scores)
        return self.value > max_other


class Classment(BaseModel):
    """
    A classment linked to a team in a tournament.
    """

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="classments")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="classments")
    rank = models.PositiveIntegerField()

    class Meta:
        unique_together = ("tournament", "team")
        ordering = ["rank"]
