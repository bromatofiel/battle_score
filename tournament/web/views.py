import random

from core.constants import COUNTRIES
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from tournament.models import Team, Tournament
from django.views.generic import FormView, TemplateView
from tournament.web.forms import TournamentForm, TournamentUpdateForm
from tournament.controllers import get_sport_controller
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin


class TournamentCreateView(LoginRequiredMixin, FormView):
    template_name = "tournament/create.html"
    form_class = TournamentForm

    def get(self, request, *args, **kwargs):
        referer = request.META.get("HTTP_REFERER")
        if referer and "create" not in referer and "menu" not in referer:
            request.session["tournament_create_next_url"] = referer
        elif not request.session.get("tournament_create_next_url"):
            request.session["tournament_create_next_url"] = "dashboard"
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sport_choices"] = Tournament.SPORTS
        context["next_url"] = self.request.session.get("tournament_create_next_url", "dashboard")
        return context

    def form_valid(self, form):
        tournament = form.save(commit=False)
        tournament.admin = self.request.user
        tournament.save()

        # Generate initial teams
        available_names = [country for country, capital in COUNTRIES]
        random.shuffle(available_names)

        nb_teams = form.cleaned_data.get("nb_teams")
        for i in range(1, int(nb_teams) + 1):
            team_name = available_names.pop() if available_names else f"Equipe {i}"
            Team.objects.create(tournament=tournament, name=team_name, number=i)

        messages.success(self.request, _("Tournoi créé avec succès !"))
        return redirect("tournament:teams", tournament_id=tournament.id)

    def form_invalid(self, form):
        messages.error(self.request, _("Veuillez corriger les erreurs ci-dessous."))
        return super().form_invalid(form)


class TournamentBaseView(LoginRequiredMixin):
    """
    Mixin to inject tournament context and common data.
    """

    def get_tournament(self):
        return get_object_or_404(Tournament, id=self.kwargs.get("tournament_id"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        context["tournament"] = tournament

        # Next 5 tournaments (admin or participant, excluding current)
        next_tournaments = (
            Tournament.objects.filter(Q(admin=self.request.user) | Q(participants__user=self.request.user))
            .exclude(id=tournament.id)
            .distinct()
            .order_by("-date_created")[:5]
        )

        context["next_tournaments"] = next_tournaments
        context["next_url"] = self.request.session.get("tournament_settings_next_url", redirect("dashboard").url)
        return context


class TournamentTeamsView(TournamentBaseView, TemplateView):
    template_name = "tournament/teams.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["teams"] = self.get_tournament().teams.all().order_by("number")
        return context


class TournamentParticipantsView(TournamentBaseView, TemplateView):
    template_name = "tournament/participants.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["participants"] = self.get_tournament().participants.all()
        return context


class TournamentMatchesView(TournamentBaseView, TemplateView):
    template_name = "tournament/matches.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["matches"] = self.get_tournament().matches.all()
        return context


class TournamentRankingView(TournamentBaseView, TemplateView):
    template_name = "tournament/ranking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        controller = get_sport_controller(tournament.sport)
        context["rankings"] = controller.get_team_scores(tournament)
        return context


class TournamentSettingsView(TournamentBaseView, FormView):
    template_name = "tournament/settings.html"
    form_class = TournamentUpdateForm

    def get(self, request, *args, **kwargs):
        # Capture referer to redirect back after success
        referer = request.META.get("HTTP_REFERER")
        if referer and "settings" not in referer and "menu" not in referer:
            request.session["tournament_settings_next_url"] = referer
        elif not request.session.get("tournament_settings_next_url"):
            request.session["tournament_settings_next_url"] = redirect("tournament:teams", tournament_id=self.get_tournament().id).url

        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_tournament()
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Paramètres mis à jour."))
        next_url = self.request.session.pop("tournament_settings_next_url", None)
        if next_url:
            return redirect(next_url)
        return redirect("tournament:settings", tournament_id=self.get_tournament().id)

    def post(self, request, *args, **kwargs):
        if request.POST.get("form_name") == "delete_tournament":
            tournament = self.get_tournament()
            tournament.delete()
            messages.success(request, _("Tournoi supprimé avec succès."))
            return redirect("dashboard")
        return super().post(request, *args, **kwargs)


class TournamentAccessView(TournamentBaseView, TemplateView):
    template_name = "tournament/access.html"
