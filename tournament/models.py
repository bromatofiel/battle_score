import random

from django.db import models
from core.utils import enum
from core.models import BaseModel
from django.conf import settings
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

    auto_match_creation = models.BooleanField(default=True)
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
        return f"Match {self.ordering} in {self.tournament.name}"


class Score(BaseModel):
    """
    A score linked to a match for a specific team.
    """

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="scores")
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    value = models.IntegerField(default=0)

    class Meta:
        unique_together = ("match", "team")


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
