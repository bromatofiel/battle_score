from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel

class Tournament(BaseModel):
    """
    A tournament with settings.
    """
    name = models.CharField(max_length=255)
    nb_teams = models.PositiveIntegerField(default=0)
    nb_players_per_team = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=255, blank=True)
    datetime = models.DateTimeField(null=True, blank=True)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="managed_tournaments")

    def __str__(self):
        return self.name

class Team(BaseModel):
    """
    A group of participants linked to a tournament.
    """
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.tournament.name})"

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
        return f"{self.user.username} in {self.tournament.name}"

class Match(BaseModel):
    """
    A match between two teams.
    """
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="matches")
    teams = models.ManyToManyField(Team, related_name="matches")
    ordering = models.PositiveIntegerField(default=0)
    datetime = models.DateTimeField(null=True, blank=True)

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
