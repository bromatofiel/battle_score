from django.urls import path
from tournament.web.views import (
    TeamCreateView,
    TeamDeleteView,
    TeamDetailView,
    TeamUpdateView,
    TournamentTeamsView,
    TournamentAccessView,
    TournamentCreateView,
    TournamentMatchesView,
    TournamentRankingView,
    TournamentSettingsView,
    TournamentParticipantsView,
)

app_name = "tournament"

urlpatterns = [
    path("create/", TournamentCreateView.as_view(), name="create"),
    path("<int:tournament_id>/", TournamentTeamsView.as_view(), name="teams"),
    path("<int:tournament_id>/participants/", TournamentParticipantsView.as_view(), name="participants"),
    path("<int:tournament_id>/matches/", TournamentMatchesView.as_view(), name="matches"),
    path("<int:tournament_id>/ranking/", TournamentRankingView.as_view(), name="ranking"),
    path("<int:tournament_id>/ranking/", TournamentRankingView.as_view(), name="ranking"),
    path("<int:tournament_id>/settings/", TournamentSettingsView.as_view(), name="settings"),
    path("<int:tournament_id>/access/", TournamentAccessView.as_view(), name="access"),
    path("<int:tournament_id>/teams/create/", TeamCreateView.as_view(), name="team_create"),
    path("<int:tournament_id>/teams/<int:team_id>/", TeamDetailView.as_view(), name="team_detail"),
    path("<int:tournament_id>/teams/<int:team_id>/update/", TeamUpdateView.as_view(), name="team_update"),
    path("<int:tournament_id>/teams/<int:team_id>/delete/", TeamDeleteView.as_view(), name="team_delete"),
]
