from django.db import transaction
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from tournament.models import Team, Tournament
from django.views.generic import FormView, DeleteView, UpdateView, TemplateView
from tournament.web.forms import TeamForm, TournamentForm, TournamentUpdateForm
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
        nb_teams = form.cleaned_data.get("nb_teams")
        team_names = Team.generate_team_names(tournament, nb_teams)
        for i in range(int(nb_teams)):
            Team.objects.create(tournament=tournament, name=team_names[i], number=i + 1)

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

    def is_tournament_admin(self, request=None):
        """Check if current user is the tournament admin."""
        req = request or self.request
        return self.get_tournament().admin == req.user

    def get_user_participation(self):
        """Get the current user's participation in the tournament."""
        from tournament.models import Participant

        return Participant.objects.filter(tournament=self.get_tournament(), user=self.request.user).first()

    def can_edit_team(self, team, request=None):
        """Check if user can edit a team (admin or team member)."""
        if self.is_tournament_admin(request):
            return True
        participation = self.get_user_participation()
        return participation and participation.team_id == team.id

    def can_delete_team(self, request=None):
        """Check if user can delete a team (admin only)."""
        return self.is_tournament_admin(request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        context["tournament"] = tournament
        context["is_admin"] = self.is_tournament_admin()

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


class TeamDetailView(TournamentBaseView, TemplateView):
    template_name = "tournament/team_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = get_object_or_404(Team, id=self.kwargs.get("team_id"), tournament__id=self.kwargs.get("tournament_id"))
        context["team"] = team
        context["members"] = team.members.all()
        context["matches"] = team.matches.all()
        context["can_edit"] = self.can_edit_team(team)
        context["can_delete"] = self.can_delete_team()
        return context


class TeamCreateView(TournamentBaseView, TemplateView):
    """View for creating multiple teams at once with auto-generated names."""

    def get_template_names(self):
        return ["tournament/team_create.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        context["teams"] = tournament.teams.all().order_by("number")
        context["teams_count"] = tournament.teams.count()
        return context

    def post(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        count = int(request.POST.get("count", 1))
        count = max(1, min(count, 50))  # Limit between 1 and 50

        team_names = Team.generate_team_names(tournament, count)
        # Get next number
        last_team = tournament.teams.order_by("-number").first()
        next_number = (last_team.number + 1) if last_team else 1

        # Create teams
        created_count = 0
        for i in range(count):
            Team.objects.create(tournament=tournament, name=team_names[i], number=next_number + i)
            created_count += 1

        if created_count == 1:
            messages.success(request, _("Équipe créée avec succès."))
        else:
            messages.success(request, _("%(count)d équipes créées avec succès.") % {"count": created_count})

        return redirect("tournament:teams", tournament_id=tournament.id)


class TeamUpdateView(TournamentBaseView, UpdateView):
    model = Team
    form_class = TeamForm
    pk_url_kwarg = "team_id"
    template_name = "tournament/team_form_partial.html"

    def get_queryset(self):
        return self.get_tournament().teams.all()

    def get(self, request, *args, **kwargs):
        if not self.can_edit_team(self.get_object()):
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden(_("Vous n'avez pas la permission de modifier cette équipe."))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.can_edit_team(self.get_object()):
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden(_("Vous n'avez pas la permission de modifier cette équipe."))
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tournament"] = self.get_tournament()
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Équipe mise à jour."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("tournament:teams", kwargs={"tournament_id": self.kwargs["tournament_id"]})


class TeamDeleteView(TournamentBaseView, DeleteView):
    model = Team
    pk_url_kwarg = "team_id"

    def get_queryset(self):
        return self.get_tournament().teams.all()

    def post(self, request, *args, **kwargs):
        """Handle POST request for team deletion."""
        if not self.can_delete_team():
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden(_("Seul l'administrateur peut supprimer une équipe."))

        self.object = self.get_object()
        tournament = self.object.tournament

        with transaction.atomic():
            self.object.delete()
            # Renumber teams to close gaps
            teams = tournament.teams.all().order_by("number")
            for i, team in enumerate(teams, start=1):
                if team.number != i:
                    team.number = i
                    team.save()

        messages.success(request, _("Équipe supprimée."))
        return redirect("tournament:teams", tournament_id=tournament.id)
