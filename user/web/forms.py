from django import forms
from user.models import User, Client, Profile
from django.utils.translation import gettext as _


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "placeholder": _("votre@email.com"),
                "class": "form-input",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            return email.lower().strip()
        return email

    password = forms.CharField(
        label=_("Mot de passe"),
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": "form-input",
            }
        ),
    )


class SignupForm(forms.ModelForm):
    pseudo = forms.CharField(
        label=_("Pseudo"),
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Votre pseudo"),
                "class": "form-input",
            }
        ),
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": "form-input",
            }
        ),
    )
    password_confirm = forms.CharField(
        label=_("Confirmer le mot de passe"),
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "class": "form-input",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "placeholder": _("votre@email.com"),
                    "class": "form-input",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower().strip()
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(_("Cet email est déjà utilisé."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", _("Les mots de passe ne correspondent pas."))

        return cleaned_data


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-input"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower().strip()
            if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
                raise forms.ValidationError(_("Cet email est déjà utilisé."))
        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["pseudo", "avatar"]
        widgets = {
            "pseudo": forms.TextInput(attrs={"class": "form-input"}),
            "avatar": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
        }


class ClientUpdateForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "address", "vat_number"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "address": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "vat_number": forms.TextInput(attrs={"class": "form-input"}),
        }


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label=_("Mot de passe pour confirmer"),
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "••••••••"}),
    )


class PasswordUpdateForm(forms.Form):
    old_password = forms.CharField(
        label=_("Ancien mot de passe"),
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "••••••••"}),
    )
    new_password = forms.CharField(
        label=_("Nouveau mot de passe"),
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "••••••••"}),
    )
    confirm_password = forms.CharField(
        label=_("Confirmer le nouveau mot de passe"),
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "••••••••"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError(_("Les deux mots de passe ne correspondent pas."))
        return cleaned_data
