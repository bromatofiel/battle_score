from django.db import transaction
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.contrib import messages
from django.db.models import Q, Count
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import FormView, DeleteView, UpdateView, TemplateView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin

from tournament.models import Team, Match, Score, Tournament
from tournament.web.forms import TeamForm, TournamentForm, TournamentUpdateForm
from tournament.controllers import get_sport_controller


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

    def can_start_tournament(self):
        """Check if tournament can be started (DRAFT or PUBLISHED only)."""
        tournament = self.get_tournament()
        return self.is_tournament_admin() and tournament.status in [
            Tournament.STATUSES.DRAFT,
            Tournament.STATUSES.PUBLISHED,
        ]

    def can_create_matches(self):
        """Check if matches can be created (ONGOING status only)."""
        tournament = self.get_tournament()
        return self.is_tournament_admin() and tournament.status == Tournament.STATUSES.ONGOING

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        context["tournament"] = tournament
        context["is_admin"] = self.is_tournament_admin()
        context["can_start_tournament"] = self.can_start_tournament()
        context["can_create_matches"] = self.can_create_matches()

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
        tournament = self.get_tournament()
        base_qs = tournament.matches.prefetch_related("teams", "scores__team")

        # Split matches into 3 sections with specific ordering:
        # - Ongoing: by start date (most recent first)
        # - Coming: by ordering (ascending, #1 before #2)
        # - Done: by end date (most recently finished first)
        matches_ongoing = base_qs.filter(status=Match.STATUSES.ONGOING).order_by("-date_start")
        matches_coming = base_qs.filter(status=Match.STATUSES.COMING).order_by("ordering")
        matches_done = base_qs.filter(status=Match.STATUSES.DONE).order_by("-date_end")

        context["matches_ongoing"] = matches_ongoing
        context["matches_coming"] = matches_coming
        context["matches_done"] = matches_done
        context["has_matches"] = matches_ongoing.exists() or matches_coming.exists() or matches_done.exists()
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
            request.session["tournament_settings_next_url"] = redirect(
                "tournament:teams", tournament_id=self.get_tournament().id
            ).url

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


class TournamentStartView(TournamentBaseView, View):
    """Start a tournament by changing its status to ONGOING."""

    def post(self, request, *args, **kwargs):
        if not self.can_start_tournament():
            return HttpResponseForbidden(_("Vous ne pouvez pas démarrer ce tournoi."))

        tournament = self.get_tournament()
        tournament.status = Tournament.STATUSES.ONGOING
        tournament.date_start = timezone.now()
        tournament.save()

        # Auto-create first matches if enabled
        if tournament.auto_match_creation and tournament.nb_team_matches:
            controller = get_sport_controller(tournament.sport)
            created = controller.create_next_matches(tournament)
            if created:
                messages.info(request, _("%(count)d match(s) créé(s) automatiquement.") % {"count": len(created)})

        messages.success(request, _("Le tournoi a démarré !"))
        return redirect("tournament:matches", tournament_id=tournament.id)


class SetAutoMatchCreationView(TournamentBaseView, View):
    """Set auto_match_creation setting for tournament."""

    def post(self, request, *args, **kwargs):
        if not self.is_tournament_admin():
            return HttpResponseForbidden(_("Seul l'administrateur peut modifier ce paramètre."))

        value = kwargs.get("value", "").lower()
        tournament = self.get_tournament()

        # Can only enable if nb_team_matches is set
        if value == "true" and not tournament.nb_team_matches:
            messages.error(request, _("Définissez d'abord le nombre de matchs par équipe."))
            return redirect("tournament:matches", tournament_id=tournament.id)

        tournament.auto_match_creation = value == "true"
        tournament.save()
        return redirect("tournament:matches", tournament_id=tournament.id)


class SetNbTeamMatchesView(TournamentBaseView, View):
    """Set nb_team_matches setting for tournament."""

    def post(self, request, *args, **kwargs):
        if not self.is_tournament_admin():
            return HttpResponseForbidden(_("Seul l'administrateur peut modifier ce paramètre."))

        tournament = self.get_tournament()
        value = request.POST.get("nb_team_matches", "").strip()

        if value:
            try:
                tournament.nb_team_matches = int(value)
            except ValueError:
                messages.error(request, _("Valeur invalide."))
                return redirect("tournament:matches", tournament_id=tournament.id)
        else:
            tournament.nb_team_matches = None
            # Disable auto if no limit set
            tournament.auto_match_creation = False

        tournament.save()
        return redirect("tournament:matches", tournament_id=tournament.id)


class MatchCreateView(TournamentBaseView, TemplateView):
    """View for creating a new match with team selection."""

    template_name = "tournament/match_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.get_tournament()
        controller = get_sport_controller(tournament.sport)
        rankings = controller.get_team_scores(tournament)

        # Build a map of team_id to rank and points
        ranking_map = {r["team"].id: {"rank": r["rank"], "points": r["total_points"]} for r in rankings}

        # Get teams with match count and ranking info
        teams = tournament.teams.annotate(match_count=Count("matches")).order_by("number")

        teams_data = []
        for team in teams:
            team_info = {
                "id": team.id,
                "number": team.number,
                "name": team.name,
                "match_count": team.match_count,
                "rank": ranking_map.get(team.id, {}).get("rank", "-"),
                "points": ranking_map.get(team.id, {}).get("points", 0),
            }
            teams_data.append(team_info)

        context["teams_data"] = teams_data
        context["default_datetime"] = timezone.now().strftime("%Y-%m-%dT%H:%M")
        return context

    def post(self, request, *args, **kwargs):
        if not self.can_create_matches():
            return HttpResponseForbidden(_("Vous ne pouvez pas créer de match."))

        tournament = self.get_tournament()
        selected_team_ids = request.POST.getlist("teams")

        if len(selected_team_ids) < 2:
            messages.error(request, _("Sélectionnez au moins 2 équipes."))
            return redirect("tournament:match_create", tournament_id=tournament.id)

        # Parse date_start
        date_start_str = request.POST.get("date_start", "")
        date_start = None
        if date_start_str:
            try:
                from django.utils.dateparse import parse_datetime

                date_start = parse_datetime(date_start_str)
                if date_start and timezone.is_naive(date_start):
                    date_start = timezone.make_aware(date_start)
            except (ValueError, TypeError):
                date_start = timezone.now()
        else:
            date_start = timezone.now()

        # Get next ordering number
        last_match = tournament.matches.order_by("-ordering").first()
        next_ordering = (last_match.ordering + 1) if last_match else 1

        # Create the match
        match = Match.objects.create(
            tournament=tournament,
            ordering=next_ordering,
            date_start=date_start,
            location=request.POST.get("location", ""),
            details=request.POST.get("details", ""),
            status=Match.STATUSES.COMING,
        )

        # Add teams to the match
        teams = Team.objects.filter(id__in=selected_team_ids, tournament=tournament)
        match.teams.set(teams)

        messages.success(request, _("Match créé avec succès."))
        return redirect("tournament:matches", tournament_id=tournament.id)


class MatchDetailView(TournamentBaseView, TemplateView):
    """View for displaying match details."""

    template_name = "tournament/match_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = get_object_or_404(Match, id=self.kwargs.get("match_id"), tournament=self.get_tournament())
        context["match"] = match
        context["match_teams"] = match.teams.all()
        context["scores"] = match.scores.select_related("team").all()
        return context


class MatchUpdateView(TournamentBaseView, TemplateView):
    """View for updating match details (admin only)."""

    template_name = "tournament/match_update.html"

    def dispatch(self, request, *args, **kwargs):
        self.kwargs = kwargs
        if not self.is_tournament_admin():
            return HttpResponseForbidden(_("Seul l'administrateur peut modifier un match."))
        return super().dispatch(request, *args, **kwargs)

    def get_match(self):
        return get_object_or_404(Match, id=self.kwargs.get("match_id"), tournament=self.get_tournament())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.get_match()
        context["match"] = match
        context["match_teams"] = match.teams.all()

        # Build team selection data like in MatchCreateView
        tournament = self.get_tournament()
        controller = get_sport_controller(tournament.sport)
        rankings = controller.get_team_scores(tournament)
        ranking_map = {r["team"].id: {"rank": r["rank"], "points": r["total_points"]} for r in rankings}

        teams = tournament.teams.annotate(match_count=Count("matches")).order_by("number")
        teams_data = []
        for team in teams:
            team_info = {
                "id": team.id,
                "number": team.number,
                "name": team.name,
                "match_count": team.match_count,
                "rank": ranking_map.get(team.id, {}).get("rank", "-"),
                "points": ranking_map.get(team.id, {}).get("points", 0),
                "selected": team in match.teams.all(),
            }
            teams_data.append(team_info)

        context["teams_data"] = teams_data
        context["date_start_value"] = match.date_start.strftime("%Y-%m-%dT%H:%M") if match.date_start else ""
        return context

    def post(self, request, *args, **kwargs):
        match = self.get_match()
        tournament = self.get_tournament()
        selected_team_ids = request.POST.getlist("teams")

        if len(selected_team_ids) < 2:
            messages.error(request, _("Sélectionnez au moins 2 équipes."))
            return redirect("tournament:match_update", tournament_id=tournament.id, match_id=match.id)

        # Parse date_start
        date_start_str = request.POST.get("date_start", "")
        if date_start_str:
            try:
                from django.utils.dateparse import parse_datetime

                date_start = parse_datetime(date_start_str)
                if date_start and timezone.is_naive(date_start):
                    date_start = timezone.make_aware(date_start)
                match.date_start = date_start
            except (ValueError, TypeError):
                pass

        match.location = request.POST.get("location", "")
        match.details = request.POST.get("details", "")

        # Track if status is changing to DONE
        old_status = match.status
        new_status = request.POST.get("status")
        valid_statuses = [s[0] for s in Match.STATUSES]
        if new_status and new_status in valid_statuses:
            match.status = new_status

        match.save()

        # Update teams
        teams = Team.objects.filter(id__in=selected_team_ids, tournament=tournament)
        match.teams.set(teams)

        # Auto-create next matches if match just finished
        if old_status != Match.STATUSES.DONE and match.status == Match.STATUSES.DONE:
            if tournament.auto_match_creation and tournament.nb_team_matches:
                controller = get_sport_controller(tournament.sport)
                created = controller.create_next_matches(tournament)
                if created:
                    messages.info(request, _("%(count)d match(s) créé(s) automatiquement.") % {"count": len(created)})

        messages.success(request, _("Match mis à jour."))
        return redirect("tournament:match_detail", tournament_id=tournament.id, match_id=match.id)


class MatchDeleteView(TournamentBaseView, View):
    """Delete a match (admin only)."""

    def post(self, request, *args, **kwargs):
        if not self.is_tournament_admin():
            return HttpResponseForbidden(_("Seul l'administrateur peut supprimer un match."))

        tournament = self.get_tournament()
        match = get_object_or_404(Match, id=kwargs.get("match_id"), tournament=tournament)

        with transaction.atomic():
            match.delete()
            # Renumber matches to close gaps
            matches = tournament.matches.all().order_by("ordering")
            for i, m in enumerate(matches, start=1):
                if m.ordering != i:
                    m.ordering = i
                    m.save()

        messages.success(request, _("Match supprimé."))
        return redirect("tournament:matches", tournament_id=tournament.id)


class ScoreUpdateView(TournamentBaseView, View):
    """Update scores for a match (admin only)."""

    def post(self, request, *args, **kwargs):
        if not self.is_tournament_admin():
            return HttpResponseForbidden(_("Seul l'administrateur peut modifier les scores."))

        tournament = self.get_tournament()
        match = get_object_or_404(Match, id=kwargs.get("match_id"), tournament=tournament)
        old_status = match.status
        has_score = False

        # Process scores for each team in the match
        for team in match.teams.all():
            score_key = f"score_{team.id}"
            score_value = request.POST.get(score_key, "").strip()

            if score_value:
                try:
                    value = int(score_value)
                    # Create or update Score
                    Score.objects.update_or_create(match=match, team=team, defaults={"value": value})
                    has_score = True
                except ValueError:
                    pass  # Skip invalid values
            else:
                # If empty, delete the score if it exists
                Score.objects.filter(match=match, team=team).delete()

        # Auto-switch to ONGOING if was COMING and a score is entered
        if match.status == Match.STATUSES.COMING and has_score:
            match.status = Match.STATUSES.ONGOING
            match.save()
            messages.info(request, _("Le match est passé en cours."))

        # Handle status change via buttons
        new_status = request.POST.get("status")
        if new_status and new_status in [s[0] for s in Match.STATUSES]:
            match.status = new_status
            match.save()

        # Auto-create next matches if match just finished
        if old_status != Match.STATUSES.DONE and match.status == Match.STATUSES.DONE:
            if tournament.auto_match_creation and tournament.nb_team_matches:
                controller = get_sport_controller(tournament)
                created = controller.create_next_matches(tournament)
                if created:
                    messages.info(request, _("%(count)d match(s) créé(s) automatiquement.") % {"count": len(created)})

        messages.success(request, _("Scores mis à jour."))
        return redirect("tournament:match_detail", tournament_id=tournament.id, match_id=match.id)
