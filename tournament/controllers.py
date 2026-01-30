import random
from abc import ABC, abstractmethod

from django.db.models import Q, Max, Count
from tournament.models import Team, Match, Tournament


class BaseSportController(ABC):
    @abstractmethod
    def get_team_scores(self, tournament: Tournament):
        """
        Returns a list of dictionaries with team and total_points, sorted by points.
        """
        raise NotImplementedError

    def create_next_matches(self, tournament: Tournament) -> list[Match]:
        """
        Creates the next matches for auto-match tournaments.
        Returns list of created matches.
        """
        if not tournament.auto_match_creation or not tournament.nb_team_matches:
            return []

        new_matches = []
        while True:
            # Search teams without enough matches
            teams = (
                tournament.teams.annotate(
                    nb_matches=Count("matches"),
                    nb_matches_pending=Count("matches", filter=Q(matches__status__in=[Match.STATUSES.COMING, Match.STATUSES.ONGOING])),
                    last_match_end=Max("matches__date_end", filter=Q(matches__status=Match.STATUSES.DONE)),
                )
                .filter(
                    nb_matches__lt=tournament.nb_team_matches,
                    nb_matches_pending=0,
                )
                .order_by(
                    "nb_matches",
                    "last_match_end",
                )
            )
            if teams:
                # Creating new match
                new_match = self._create_single_match(tournament, teams[0])
                if new_match:
                    new_matches.append(new_match)
            else:
                break
        return new_matches

    def _create_single_match(self, tournament: Tournament, team: Team) -> Match | None:
        """
        Creates a match for a team and returns the created match or None if no match can be created.
        """
        team_encounters = {team: {"nb_matches": 0, "last_match": None} for team in tournament.teams.all() if team != team}
        min_encouters = float("inf")

        # Listing opponents encounters and last match date
        for match in team.matches.prefetch_related("teams").all():
            for competitor in match.teams.all():
                if competitor != team:
                    team_encounters[competitor]["nb_matches"] += 1
                    team_encounters[competitor]["last_match"] = max(team_encounters[competitor]["last_match"], match.date_created)
                    min_encouters = min(min_encouters, team_encounters[competitor]["nb_matches"])

        # Selecting opponent with less encounters or oldest match
        candidates = [team for team, data in team_encounters.items() if data["nb_matches"] == min_encouters]
        if min_encouters == 0:
            random.shuffle(candidates)
        else:
            candidates.sort(key=lambda x: team_encounters[x]["last_match"])

        # Creating match
        opponents = [team, candidates[0]]  # TODO: add a way to know how many teams must join the match
        last_match = tournament.matches.order_by("-ordering").first()
        next_ordering = (last_match.ordering + 1) if last_match else 1
        return Match.objects.create(tournament=tournament, teams=opponents, ordering=next_ordering, status=Match.STATUSES.COMING)


class GenericSportController(BaseSportController):
    def get_team_scores(self, tournament: Tournament):
        teams = tournament.teams.all()
        team_points = {team.id: 0 for team in teams}

        matches = tournament.matches.prefetch_related("scores")
        for match in matches:
            scores = list(match.scores.all())
            if len(scores) < 2:
                continue

            # Assuming 2 teams per match based on requirements
            s1, s2 = scores[0], scores[1]

            if s1.value > s2.value:
                team_points[s1.team_id] += 1
            elif s2.value > s1.value:
                team_points[s2.team_id] += 1
            else:
                # Draw: both teams get 1 point
                team_points[s1.team_id] += 1
                team_points[s2.team_id] += 1

        rankings = []
        for team in teams:
            rankings.append({"team": team, "total_points": team_points.get(team.id, 0)})

        # Sort by points descending
        sorted_rankings = sorted(rankings, key=lambda x: x["total_points"], reverse=True)

        # Calculate ranks with ties (competitive ranking)
        current_rank = 0
        current_points = -1
        for i, item in enumerate(sorted_rankings):
            if item["total_points"] != current_points:
                current_rank = i + 1
                current_points = item["total_points"]
            item["rank"] = current_rank

        return sorted_rankings


class PetanqueSportController(GenericSportController):
    # For now, Petanque uses the same basic scoring logic as Generic
    # but we can specialize it later (e.g., number of wins vs points)
    pass


def get_sport_controller(sport_name: str) -> BaseSportController:
    controllers = {
        Tournament.SPORTS.PETANQUE: PetanqueSportController(),
        Tournament.SPORTS.GENERIC: GenericSportController(),
    }
    return controllers.get(sport_name, GenericSportController())
