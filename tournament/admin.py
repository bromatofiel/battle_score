from core.admins import BaseAdmin
from django.contrib import admin
from .models import Team, Match, Score, Classment, Tournament, Participant


@admin.register(Tournament)
class TournamentAdmin(BaseAdmin):
    list_display = ("name", "sport", "admin", "nb_teams", "nb_players_per_team", "auto_match_creation", "status", "date_start", "date_end")
    list_filter = ("sport", "status", "auto_match_creation")
    search_fields = ("name", "location")


@admin.register(Team)
class TeamAdmin(BaseAdmin):
    list_display = ("name", "number", "tournament", "date_created")
    list_filter = ("tournament",)
    search_fields = ("name", "tournament__name")


@admin.register(Participant)
class ParticipantAdmin(BaseAdmin):
    list_display = ("user", "tournament", "team", "role", "date_created")
    list_filter = ("tournament", "role")
    search_fields = ("user__email", "user__username", "tournament__name")


@admin.register(Match)
class MatchAdmin(BaseAdmin):
    list_display = ("tournament", "ordering", "status", "date_start", "date_end", "date_created")
    list_filter = ("tournament", "status")
    ordering = ("tournament", "ordering")
    search_field = ("tournament__name", "teams__name", "location", "details")


@admin.register(Score)
class ScoreAdmin(BaseAdmin):
    list_display = ("match", "team", "value", "date_created")
    list_filter = ("match__tournament",)


@admin.register(Classment)
class ClassmentAdmin(BaseAdmin):
    list_display = ("tournament", "team", "rank", "date_created")
    list_filter = ("tournament",)
    ordering = ("tournament", "rank")
