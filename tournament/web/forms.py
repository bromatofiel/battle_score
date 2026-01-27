from django import forms
from tournament.models import Team, Tournament


class TournamentForm(forms.ModelForm):
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}))
    time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time", "class": "form-input", "step": "60"}))

    class Meta:
        model = Tournament
        fields = ["name", "sport", "description", "nb_teams", "nb_players_per_team", "location"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "x-model": "name"}),
            "sport": forms.HiddenInput(attrs={"x-model": "sport"}),
            "nb_teams": forms.HiddenInput(attrs={":value": "nbTeams"}),
            "nb_players_per_team": forms.HiddenInput(attrs={":value": "nbPlayersPerTeam"}),
            "description": forms.Textarea(attrs={"class": "form-input leading-relaxed", "rows": 3}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        time = cleaned_data.get("time")

        if date and time:
            import datetime

            from django.utils import timezone

            combined_datetime = timezone.make_aware(datetime.datetime.combine(date, time))
            cleaned_data["datetime"] = combined_datetime

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.datetime = self.cleaned_data.get("datetime")
        if commit:
            instance.save()
        return instance


class TournamentUpdateForm(forms.ModelForm):
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}))
    time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time", "class": "form-input", "step": "60"}))

    class Meta:
        model = Tournament
        fields = ["name", "sport", "description", "nb_teams", "nb_players_per_team", "location"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "sport": forms.Select(attrs={"class": "form-input"}),
            "nb_teams": forms.NumberInput(attrs={"class": "form-input"}),
            "nb_players_per_team": forms.NumberInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input leading-relaxed", "rows": 3}),
            "location": forms.TextInput(attrs={"class": "form-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        time = cleaned_data.get("time")

        if date and time:
            import datetime

            from django.utils import timezone

            combined_datetime = timezone.make_aware(datetime.datetime.combine(date, time))
            cleaned_data["datetime"] = combined_datetime
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if "datetime" in self.cleaned_data:
            instance.datetime = self.cleaned_data.get("datetime")
        if commit:
            instance.save()
        return instance


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "number"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "number": forms.NumberInput(attrs={"class": "form-input", "readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        self.tournament = kwargs.pop("tournament", None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk and self.tournament:
            initial_name = Team.generate_team_names(self.tournament, 1)[0]
            self.fields["name"].initial = initial_name

            # Assign next available number
            last_team = self.tournament.teams.order_by("-number").first()
            self.fields["number"].initial = (last_team.number + 1) if last_team else 1

        if self.instance.pk:
            self.fields["number"].widget.attrs["readonly"] = True
