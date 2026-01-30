from django.urls import path
from tournament.web.views import (
    TeamCreateView,
    TeamDeleteView,
    TeamDetailView,
    TeamUpdateView,
    MatchCreateView,
    MatchDeleteView,
    MatchDetailView,
    MatchUpdateView,
    TournamentStartView,
    TournamentTeamsView,
    SetNbTeamMatchesView,
    TournamentAccessView,
    TournamentCreateView,
    TournamentMatchesView,
    TournamentRankingView,
    TournamentSettingsView,
    SetAutoMatchCreationView,
    TournamentParticipantsView,
)

app_name = "tournament"

urlpatterns = [
    path("create/", TournamentCreateView.as_view(), name="create"),
    path("<int:tournament_id>/", TournamentTeamsView.as_view(), name="teams"),
    path("<int:tournament_id>/start/", TournamentStartView.as_view(), name="start"),
    path("<int:tournament_id>/participants/", TournamentParticipantsView.as_view(), name="participants"),
    path("<int:tournament_id>/matches/", TournamentMatchesView.as_view(), name="matches"),
    path("<int:tournament_id>/matches/create/", MatchCreateView.as_view(), name="match_create"),
    path("<int:tournament_id>/matches/<int:match_id>/", MatchDetailView.as_view(), name="match_detail"),
    path("<int:tournament_id>/matches/<int:match_id>/update/", MatchUpdateView.as_view(), name="match_update"),
    path("<int:tournament_id>/matches/<int:match_id>/delete/", MatchDeleteView.as_view(), name="match_delete"),
    path("<int:tournament_id>/ranking/", TournamentRankingView.as_view(), name="ranking"),
    path("<int:tournament_id>/settings/", TournamentSettingsView.as_view(), name="settings"),
    path("<int:tournament_id>/access/", TournamentAccessView.as_view(), name="access"),
    path("<int:tournament_id>/set-auto-match/<str:value>/", SetAutoMatchCreationView.as_view(), name="set_auto_match"),
    path("<int:tournament_id>/set-nb-team-matches/", SetNbTeamMatchesView.as_view(), name="set_nb_team_matches"),
    path("<int:tournament_id>/teams/create/", TeamCreateView.as_view(), name="team_create"),
    path("<int:tournament_id>/teams/<int:team_id>/", TeamDetailView.as_view(), name="team_detail"),
    path("<int:tournament_id>/teams/<int:team_id>/update/", TeamUpdateView.as_view(), name="team_update"),
    path("<int:tournament_id>/teams/<int:team_id>/delete/", TeamDeleteView.as_view(), name="team_delete"),
]
