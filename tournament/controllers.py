from abc import ABC, abstractmethod

from tournament.models import Tournament


class BaseSportController(ABC):
    @abstractmethod
    def get_team_scores(self, tournament: Tournament):
        """
        Returns a list of dictionaries with team and total_points, sorted by points.
        """
        raise NotImplementedError


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
        return sorted(rankings, key=lambda x: x["total_points"], reverse=True)


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
