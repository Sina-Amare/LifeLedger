# accounts/tests.py

import uuid
import os
import shutil

from django.test import TestCase, Client, override_settings
from django.urls import reverse, reverse_lazy
from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.sites.models import Site
from django.conf import settings
from django.forms.forms import NON_FIELD_ERRORS
from django.utils.html import escape

from .models import UserProfile
from .forms import CustomUserCreationForm, UsernameEmailAuthenticationForm, ResendActivationEmailForm

User = get_user_model()

TEST_MEDIA_ROOT = os.path.join(settings.BASE_DIR, f'test_media_root_accounts_app_{uuid.uuid4().hex[:8]}')

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AccountsModelTests(TestCase):
    def setUp(self):
        self.username = f"test_model_user_{uuid.uuid4().hex[:6]}"
        self.email = f"{self.username}@example.com"
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password="password123"
        )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)
        super().tearDownClass()

    def test_custom_user_str(self):
        self.assertEqual(str(self.user), self.user.username)

    def test_user_profile_creation_and_methods(self):
        profile, created = UserProfile.objects.get_or_create(user=self.user)
        self.assertTrue(created or UserProfile.objects.filter(user=self.user).exists())
        self.assertEqual(str(profile), f'Profile for {self.user.username}')

        self.assertIsNone(profile.activation_key)
        profile.generate_activation_key()
        self.assertIsNotNone(profile.activation_key)
        self.assertEqual(len(profile.activation_key), 36) 

        self.user.is_active = False
        self.user.save()
        profile.activation_key = "some_test_key_123_model_v3" 
        profile.save()

        profile.activate_user()
        self.user.refresh_from_db()
        profile.refresh_from_db()

        self.assertTrue(self.user.is_active)
        self.assertIsNone(profile.activation_key)


class AccountsFormTests(TestCase):
    def test_custom_user_creation_form_valid(self):
        username = f'form_valid_user_{uuid.uuid4().hex[:6]}'
        email = f'{username}@example.com'
        form_data = {
            'username': username, 'email': email,
            'password1': 'ValidPass123!', 'password2': 'ValidPass123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_custom_user_creation_form_password_mismatch(self):
        form_data = {
            'username': f'mismatch_form_{uuid.uuid4().hex[:6]}',
            'email': f'mismatch_form_{uuid.uuid4().hex[:6]}@example.com',
            'password1': 'ValidPass123!', 'password2': 'DifferentPass123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        self.assertIn("The two password fields didn’t match.", form.errors['password2'])

    def test_custom_user_creation_form_existing_active_email(self):
        active_email = f'existing_active_form_{uuid.uuid4().hex[:6]}@example.com'
        User.objects.create_user(username=f'existing_active_user_form_{uuid.uuid4().hex[:4]}', email=active_email, password='password')
        form_data = {
            'username': f'new_user_dup_active_email_form_{uuid.uuid4().hex[:6]}',
            'email': active_email, 'password1': 'ValidPass123!', 'password2': 'ValidPass123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn("This email address is already in use.", form.errors['email'])

    def test_custom_user_creation_form_existing_inactive_email(self):
        inactive_email = f'existing_inactive_form_{uuid.uuid4().hex[:6]}@example.com'
        User.objects.create_user(username=f'existing_inactive_user_form_{uuid.uuid4().hex[:4]}', email=inactive_email, password='password', is_active=False)
        form_data = {
            'username': f'new_user_dup_inactive_email_form_{uuid.uuid4().hex[:6]}',
            'email': inactive_email, 'password1': 'ValidPass123!', 'password2': 'ValidPass123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn(
            "An account with this email already exists but is not active. "
            "Please use the 'Resend Activation Email' option if you haven't received the activation link.",
            form.errors['email'][0] 
        )

    def test_username_email_authentication_form_inactive_user(self):
        inactive_username = f'auth_inactive_user_form_{uuid.uuid4().hex[:6]}'
        User.objects.create_user(username=inactive_username, email=f'{inactive_username}@example.com', password='password123', is_active=False)
        form_data = {'username': inactive_username, 'password': 'password123'}
        request = Client().request().wsgi_request 
        form = UsernameEmailAuthenticationForm(request=request, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        self.assertIn(
            "Your account is not active. Please check your email for the activation link or use the 'Resend Activation Email' option.",
            form.errors[NON_FIELD_ERRORS]
        )

    def test_username_email_authentication_form_invalid_credentials(self):
        active_username = f'auth_active_user_form_{uuid.uuid4().hex[:6]}'
        User.objects.create_user(username=active_username, email=f'{active_username}@example.com', password='password123', is_active=True)
        form_data = {'username': active_username, 'password': 'wrongpassword'}
        request = Client().request().wsgi_request 
        form = UsernameEmailAuthenticationForm(request=request, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        self.assertIn(
            "Please enter a correct username and password. Note that both fields may be case-sensitive.",
            form.errors[NON_FIELD_ERRORS]
        )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class AccountsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.active_user_username = f'active_view_final_v3_{uuid.uuid4().hex[:6]}'
        self.active_user = User.objects.create_user(
            username=self.active_user_username, email=f'{self.active_user_username}@example.com', 
            password='password123', is_active=True
        )
        self.inactive_user_username = f'inactive_view_final_v3_{uuid.uuid4().hex[:6]}'
        self.inactive_user = User.objects.create_user(
            username=self.inactive_user_username, email=f'{self.inactive_user_username}@example.com', 
            password='password123', is_active=False
        )
        self.inactive_profile, _ = UserProfile.objects.get_or_create(user=self.inactive_user)
        self.inactive_profile.generate_activation_key()

        site = Site.objects.get(id=settings.SITE_ID)
        site.domain = 'testserver'
        site.name = 'testserver'
        site.save()
        mail.outbox = []

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)
        super().tearDownClass()

    def test_home_view_unauthenticated(self):
        response = self.client.get(reverse('accounts:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_home_view_authenticated(self):
        self.client.login(username=self.active_user_username, password='password123')
        response = self.client.get(reverse('accounts:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard.html')
        self.assertContains(response, self.active_user_username, html=True)
        self.client.logout()

    def test_signup_view_creates_inactive_user_and_sends_email(self):
        signup_username = f'signup_test_final_v5_{uuid.uuid4().hex[:6]}'
        signup_email = f'{signup_username}@example.com'
        response = self.client.post(reverse('accounts:signup'), {
            'username': signup_username, 'email': signup_email,
            'password1': 'TestPass123!', 'password2': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('accounts:account_activation_sent'))
        new_user = User.objects.get(username=signup_username)
        self.assertFalse(new_user.is_active)
        self.assertTrue(hasattr(new_user, 'profile'))
        self.assertIsNotNone(new_user.profile.activation_key)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(new_user.profile.activation_key, mail.outbox[0].body)

    def test_signup_view_invalid_form(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': f'signup_test_final_v5_{uuid.uuid4().hex[:6]}',
            'email': f'signup_test_final_v5_{uuid.uuid4().hex[:6]}@example.com',
            'password1': 'TestPass123!', 'password2': 'DifferentPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'password2', "The two password fields didn’t match.")

    def test_account_activation_view_valid_key(self):
        response = self.client.get(reverse('accounts:activate', kwargs={'activation_key': self.inactive_profile.activation_key}))
        self.assertRedirects(response, reverse('accounts:account_activation_success'))
        self.inactive_user.refresh_from_db()
        self.assertTrue(self.inactive_user.is_active)

    def test_account_activation_view_invalid_key(self):
        response = self.client.get(reverse('accounts:activate', kwargs={'activation_key': 'invalid-key'}))
        self.assertRedirects(response, reverse('accounts:account_activation_invalid'))
        self.inactive_user.refresh_from_db()
        self.assertFalse(self.inactive_user.is_active)

    def test_login_view_inactive_user(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': self.inactive_user_username, 'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], None, 
                             "Your account is not active. Please check your email for the activation link or use the 'Resend Activation Email' option.")

    @override_settings(LOGIN_REDIRECT_URL='/accounts/')
    def test_login_view_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': self.active_user_username, 'password': 'password123'
        })
        self.assertRedirects(response, reverse('accounts:home'))
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_logout_view(self):
        self.client.login(username=self.active_user_username, password='password123')
        self.assertTrue('_auth_user_id' in self.client.session)
        
        response_confirm = self.client.get(reverse('accounts:logout_confirm'))
        self.assertEqual(response_confirm.status_code, 200)
        self.assertContains(response_confirm, f"Are you sure you want to log out, {self.active_user_username}?")
        response_logout = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response_logout, reverse('accounts:home')) 
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_resend_activation_email_view_inactive_user(self):
        old_key = self.inactive_profile.activation_key
        response = self.client.post(reverse('accounts:resend_activation_email'), {'username_or_email': self.inactive_user.email})
        self.assertRedirects(response, reverse('accounts:resend_activation_email_sent'))
        self.assertEqual(len(mail.outbox), 1)
        self.inactive_profile.refresh_from_db()
        self.assertNotEqual(self.inactive_profile.activation_key, old_key)

    def test_resend_activation_email_view_active_user(self):
        response = self.client.post(reverse('accounts:resend_activation_email'), {'username_or_email': self.active_user.email})
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('username_or_email', form.errors)
        self.assertIn(
            "This account is already active. Please try logging in.",
            form.errors['username_or_email']
        )

    def test_password_reset_view_sends_email(self):
        response = self.client.post(reverse('accounts:password_reset'), {'email': self.active_user.email})
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.active_user.email])

    def test_password_reset_view_invalid_email(self):
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'nonexistent@example.com'})
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_static_template_views_render(self):
        pages_to_test_unauthenticated = [
            'accounts:account_activation_sent', 'accounts:account_activation_success',
            'accounts:account_activation_invalid', 'accounts:resend_activation_email_sent',
            'accounts:password_reset_done', 'accounts:password_reset_complete',
        ]
        for page_name in pages_to_test_unauthenticated:
            response = self.client.get(reverse(page_name))
            self.assertEqual(response.status_code, 200, f"Page {page_name} failed to load. Status: {response.status_code}")

        self.client.login(username=self.active_user_username, password='password123')
        response = self.client.get(reverse('accounts:logout_confirm'))
        self.assertEqual(response.status_code, 200, "Page accounts:logout_confirm failed to load.")
        self.client.logout()