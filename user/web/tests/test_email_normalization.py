from django.test import TestCase
from user.models import User
from user.web.forms import LoginForm, SignupForm, UserUpdateForm


class TestUserEmailNormalization(TestCase):
    def test_login_form_normalization(self):
        form = LoginForm(data={"email": "  USER@Example.COM  ", "password": "password123"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "user@example.com")

    def test_signup_form_normalization(self):
        form = SignupForm(
            data={"email": "  NewUser@Example.COM  ", "pseudo": "testuser", "password": "password123", "password_confirm": "password123"}
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "newuser@example.com")

    def test_signup_form_uniqueness_normalized(self):
        User.objects.create_user(email="taken@example.com", username="taken@example.com", password="password123")
        # Try to sign up with the same email but different casing/spaces
        form = SignupForm(
            data={"email": "  TAKEN@Example.COM  ", "pseudo": "testuser2", "password": "password123", "password_confirm": "password123"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_user_update_form_normalization(self):
        user = User.objects.create_user(email="old@example.com", username="old@example.com", password="password123")
        form = UserUpdateForm(data={"email": "  NEW@Example.COM  "}, instance=user)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "new@example.com")

    def test_user_update_form_uniqueness_normalized(self):
        User.objects.create_user(email="other@example.com", username="other@example.com", password="password123")
        user = User.objects.create_user(email="me@example.com", username="me@example.com", password="password123")

        form = UserUpdateForm(data={"email": "  OTHER@Example.COM  "}, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
