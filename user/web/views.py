from user.models import Client
from django.views import View
from django.contrib import messages
from user.web.forms import LoginForm, SignupForm, UserUpdateForm, ClientUpdateForm, DeleteAccountForm, ProfileUpdateForm, PasswordUpdateForm
from django.shortcuts import render, redirect
from user.controllers import UserController
from tournament.models import Tournament, Participant
from django.contrib.auth import login, logout, authenticate
from django.views.generic import FormView, TemplateView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin


class LoginView(FormView):
    template_name = "user/login.html"
    form_class = LoginForm

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            next_url = request.GET.get("next") or "dashboard"
            return redirect(next_url)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        user = authenticate(self.request, email=email, password=password)
        if user:
            login(self.request, user)
            next_url = self.request.GET.get("next") or "home"
            return redirect(next_url)
        else:
            messages.error(self.request, "Email ou mot de passe invalide.")
            return self.form_invalid(form)


class SignupView(FormView):
    template_name = "user/signup.html"
    form_class = SignupForm

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            next_url = request.GET.get("next") or "dashboard"
            return redirect(next_url)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        UserController.create_user(
            email=form.cleaned_data["email"],
            pseudo=form.cleaned_data["pseudo"],
            password=form.cleaned_data["password"],
        )
        messages.success(self.request, _("Compte créé avec succès. Vous pouvez maintenant vous connecter."))
        return redirect("login")


class HomeView(TemplateView):
    template_name = "user/home.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().get(request, *args, **kwargs)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("home")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "user/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Tournaments managed by the user
        context["managed_tournaments"] = Tournament.objects.filter(admin=self.request.user)
        # Tournaments where the user is a participant
        context["participations"] = Participant.objects.filter(user=self.request.user).select_related("tournament")
        return context


class AccountSettingsView(LoginRequiredMixin, View):
    template_name = "user/settings.html"

    def get_client(self):
        client = Client.objects.filter(user=self.request.user).first()
        if not client:
            client = Client(user=self.request.user)
        return client

    def get_context_data(self, **kwargs):
        user = self.request.user
        profile = getattr(user, "profile", None)
        client = self.get_client()

        context = {
            "user_form": kwargs.get("user_form", UserUpdateForm(instance=user)),
            "profile_form": kwargs.get("profile_form", ProfileUpdateForm(instance=profile)),
            "client_form": kwargs.get("client_form", ClientUpdateForm(instance=client)),
            "delete_form": kwargs.get("delete_form", DeleteAccountForm()),
            "password_form": kwargs.get("password_form", PasswordUpdateForm()),
        }
        return context

    def get(self, request):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request):
        user = request.user
        profile = getattr(user, "profile", None)
        client = self.get_client()

        # Determine which form was submitted using a hidden input or button name
        form_name = request.POST.get("form_name")

        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile)
        client_form = ClientUpdateForm(instance=client)
        delete_form = DeleteAccountForm()
        password_form = PasswordUpdateForm()

        success = False

        if form_name == "user":
            user_form = UserUpdateForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                success = True
        elif form_name == "profile":
            profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                success = True
        elif form_name == "client":
            client_form = ClientUpdateForm(request.POST, instance=client)
            if client_form.is_valid():
                client_form.save()
                success = True
        elif form_name == "delete_account":
            delete_form = DeleteAccountForm(request.POST)
            if delete_form.is_valid():
                password = delete_form.cleaned_data.get("password")
                if UserController.delete_user(user, password):
                    messages.success(request, _("Votre compte a été supprimé."))
                    return redirect("home")
                else:
                    delete_form.add_error("password", _("Mot de passe incorrect."))
        elif form_name == "password":
            password_form = PasswordUpdateForm(request.POST)
            if password_form.is_valid():
                old_password = password_form.cleaned_data.get("old_password")
                new_password = password_form.cleaned_data.get("new_password")
                if UserController.update_password(user, old_password, new_password):
                    messages.success(request, _("Mot de passe mis à jour avec succès. Veuillez vous reconnecter."))
                    logout(request)
                    return redirect("login")
                else:
                    password_form.add_error("old_password", _("Ancien mot de passe incorrect."))

        if success:
            messages.success(request, _("Modifications enregistrées avec succès."))
            return redirect("settings")

        context = {
            "user_form": user_form,
            "profile_form": profile_form,
            "client_form": client_form,
            "delete_form": delete_form,
            "password_form": password_form,
        }
        return render(request, self.template_name, context)
