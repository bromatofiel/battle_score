import random

from core.constants import COUNTRIES
from django.contrib import messages
from django.shortcuts import redirect
from tournament.models import Team, Tournament
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin


class TournamentCreateView(LoginRequiredMixin, TemplateView):
    template_name = "tournament/create.html"

    def post(self, request, *args, **kwargs):
        # Final creation logic
        sport = request.POST.get("sport")
        nb_teams = request.POST.get("nb_teams", 5)
        nb_players_per_team = request.POST.get("nb_players_per_team", 4)
        name = request.POST.get("name", f"Tournois {sport}")
        description = request.POST.get("description", "")
        location = request.POST.get("location", "")
        # date and time would need parsing, but for now simple

        tournament = Tournament.objects.create(
            admin=request.user,
            name=name,
            sport=sport,
            description=description,
            nb_teams=nb_teams,
            nb_players_per_team=nb_players_per_team,
            location=location,
        )

        # Generate initial teams
        available_names = [capital for _, capital in COUNTRIES]
        random.shuffle(available_names)

        for i in range(1, int(nb_teams) + 1):
            team_name = available_names.pop() if available_names else f"Equipe {i}"
            Team.objects.create(tournament=tournament, name=team_name, number=i)

        messages.success(request, _("Tournoi créé avec succès !"))
        return redirect("dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sport_choices"] = Tournament.SPORTS
        return context
