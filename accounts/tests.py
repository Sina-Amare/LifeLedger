import uuid
import os
import shutil
import re # Import re for regex

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.sites.models import Site
from django.conf import settings
from django.forms.forms import NON_FIELD_ERRORS
from django.http import HttpResponseRedirect

from user_profile.models import UserProfile 
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

    def test_user_profile_creation_via_signal_and_methods(self):
        self.assertTrue(hasattr(self.user, 'profile'), "User instance should have a 'profile' attribute.")
        profile = self.user.profile 
        self.assertIsNotNone(profile, "User's profile should not be None.")
        self.assertIsInstance(profile, UserProfile, "User's profile should be an instance of the imported UserProfile.")
        self.assertEqual(str(profile), f'Profile for {self.user.username}')
        self.assertIsNone(profile.activation_key, "New profile's activation_key should be None initially.")
        
        key_value = profile.generate_activation_key_value()
        profile.activation_key = key_value
        profile.save() 
        self.assertIsNotNone(profile.activation_key, "activation_key should be set after generation and save.")
        self.assertEqual(len(profile.activation_key), 36, "Activation key should be a 36-character UUID string.") 

        self.user.is_active = False
        self.user.save()
        profile.refresh_from_db() 
        if not profile.activation_key: 
            key_for_activation = profile.generate_activation_key_value()
            profile.activation_key = key_for_activation
            profile.save()
            
        profile.activate_user_account() 
        
        self.user.refresh_from_db() 
        profile.refresh_from_db() 

        self.assertTrue(self.user.is_active, "User should be active after calling activate_user_account.")
        self.assertIsNone(profile.activation_key, "activation_key should be None after activation.")


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
        client = Client()
        request = client.request().wsgi_request 
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
        client = Client()
        request = client.request().wsgi_request
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
        self.active_user_username = f'active_view_final_v4_{uuid.uuid4().hex[:6]}'
        self.active_user = User.objects.create_user(
            username=self.active_user_username, email=f'{self.active_user_username}@example.com', 
            password='password123', is_active=True
        )
        self.inactive_user_username = f'inactive_view_final_v4_{uuid.uuid4().hex[:6]}'
        self.inactive_user = User.objects.create_user(
            username=self.inactive_user_username, email=f'{self.inactive_user_username}@example.com', 
            password='password123', is_active=False
        )
        self.assertTrue(hasattr(self.inactive_user, 'profile'), "Inactive user should have a profile attribute after creation.")
        self.inactive_user_profile = self.inactive_user.profile 
        self.assertIsNotNone(self.inactive_user_profile, "Inactive user's profile should not be None.")
        key_value = self.inactive_user_profile.generate_activation_key_value()
        self.inactive_user_profile.activation_key = key_value
        self.inactive_user_profile.save()
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
        self.client.logout()

    def test_signup_view_creates_inactive_user_and_sends_email(self):
        mail.outbox = [] 
        signup_username = f'signup_test_final_v6_{uuid.uuid4().hex[:6]}'
        signup_email = f'{signup_username}@example.com'
        response = self.client.post(reverse('accounts:signup'), {
            'username': signup_username, 'email': signup_email,
            'password1': 'TestPass123!', 'password2': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('accounts:account_activation_sent'))
        try:
            new_user = User.objects.get(username=signup_username)
        except User.DoesNotExist:
            self.fail("User was not created by signup view.")
        self.assertFalse(new_user.is_active, "Newly signed up user should be inactive.")
        self.assertTrue(hasattr(new_user, 'profile'), "Newly signed up user should have a profile attribute.")
        self.assertIsNotNone(new_user.profile, "User's profile should not be None after signup.")
        self.assertIsInstance(new_user.profile, UserProfile, "User's profile should be an instance of the new UserProfile model.")
        self.assertIsNotNone(new_user.profile.activation_key, "User's profile should have an activation key after signup view processing.")
        self.assertEqual(len(mail.outbox), 1, "One activation email should have been sent.")
        sent_email = mail.outbox[0]
        self.assertIn(new_user.profile.activation_key, sent_email.body, "Activation key should be in the email body.")
        if sent_email.alternatives: 
             self.assertIn(new_user.profile.activation_key, sent_email.alternatives[0][0], "Activation key should be in the HTML part of email body.")

    def test_signup_view_invalid_form(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': f'signup_invalid_form_test_{uuid.uuid4().hex[:6]}',
            'email': f'signup_invalid_form_test_{uuid.uuid4().hex[:6]}@example.com',
            'password1': 'TestPass123!', 'password2': 'DifferentPass123!'
        })
        self.assertEqual(response.status_code, 200) 
        self.assertFormError(response.context['form'], 'password2', "The two password fields didn’t match.")

    def test_account_activation_view_valid_key(self):
        self.assertFalse(self.inactive_user.is_active)
        self.assertIsNotNone(self.inactive_user_profile.activation_key)
        activation_url = reverse('accounts:activate', kwargs={'activation_key': self.inactive_user_profile.activation_key})
        response = self.client.get(activation_url)
        self.assertRedirects(response, reverse('accounts:account_activation_success'), 
                             msg_prefix=f"Activation failed. Response status: {response.status_code}. Location: {response.get('location', 'N/A')}")
        self.inactive_user.refresh_from_db() 
        self.assertTrue(self.inactive_user.is_active, "User should be active after valid key activation.")
        self.inactive_user_profile.refresh_from_db()
        self.assertIsNone(self.inactive_user_profile.activation_key, "Activation key should be cleared after successful activation.")

    def test_account_activation_view_invalid_key(self):
        response = self.client.get(reverse('accounts:activate', kwargs={'activation_key': 'this-is-an-invalid-key'}))
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

    def test_login_view_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': self.active_user_username, 'password': 'password123'
        })
        expected_redirect_url = settings.LOGIN_REDIRECT_URL
        self.assertRedirects(response, expected_redirect_url, 
                             msg_prefix=f"Login redirect failed. Expected {expected_redirect_url}, got {response.get('location')}")
        self.assertTrue('_auth_user_id' in self.client.session, "User should be logged in (session contains _auth_user_id).")

    def test_logout_view(self):
        self.client.login(username=self.active_user_username, password='password123')
        self.assertTrue('_auth_user_id' in self.client.session)
        response_confirm = self.client.get(reverse('accounts:logout_confirm'))
        self.assertEqual(response_confirm.status_code, 200)
        response_logout = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response_logout, reverse('accounts:home')) 
        self.assertFalse('_auth_user_id' in self.client.session, "User should be logged out (session should not contain _auth_user_id).")

    def test_resend_activation_email_view_inactive_user(self):
        mail.outbox = [] 
        self.assertFalse(self.inactive_user.is_active)
        old_key = self.inactive_user_profile.activation_key
        self.assertIsNotNone(old_key)
        response = self.client.post(reverse('accounts:resend_activation_email'), 
                                    {'username_or_email': self.inactive_user.email})
        self.assertRedirects(response, reverse('accounts:resend_activation_email_sent'))
        self.assertEqual(len(mail.outbox), 1, "One activation email should have been resent.")
        self.inactive_user_profile.refresh_from_db() 
        self.assertNotEqual(self.inactive_user_profile.activation_key, old_key, "Activation key should have changed after resend.")
        self.assertIsNotNone(self.inactive_user_profile.activation_key, "New activation key should not be None.")
        self.assertIn(self.inactive_user_profile.activation_key, mail.outbox[0].body)

    def test_resend_activation_email_view_active_user(self):
        mail.outbox = []
        response = self.client.post(reverse('accounts:resend_activation_email'), 
                                    {'username_or_email': self.active_user.email})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/resend_activation_email.html')
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('username_or_email', form.errors)
        self.assertIn(
            "This account is already active. Please try logging in.",
            form.errors['username_or_email']
        )
        self.assertEqual(len(mail.outbox), 0) 

    def test_password_reset_views_flow(self):
        mail.outbox = []
        self.client.logout() # Ensure client is logged out

        # 1. Request password reset
        response_request_reset = self.client.post(reverse('accounts:password_reset'), {'email': self.active_user.email})
        self.assertRedirects(response_request_reset, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1, "Password reset email should be sent.")
        
        email_body = mail.outbox[0].body
        match = re.search(r'accounts/password-reset/confirm/([A-Za-z0-9_\-]+)/([A-Za-z0-9_\-]+-[A-Za-z0-9\-]+)/', email_body)
        self.assertIsNotNone(match, f"Could not find password reset link in email. Email body: {email_body}")
        uidb64, token = match.groups()

        # 2. Visit password reset confirm link (initial GET with token from email)
        reset_url_with_token = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
        response_initial_get = self.client.get(reset_url_with_token)
        
        # Expect a redirect to the URL with 'set-password' as the token
        self.assertEqual(response_initial_get.status_code, 302, 
                         f"Initial GET to reset link should redirect. Got {response_initial_get.status_code}")
        
        expected_redirect_url_for_form = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': 'set-password'})
        # Check if the redirect URL matches, ignoring potential trailing slashes if one has it and other doesn't
        self.assertURLEqual(response_initial_get.url, expected_redirect_url_for_form, 
                            f"Redirect URL mismatch. Got {response_initial_get.url}, expected {expected_redirect_url_for_form}")

        # 3. GET the page that actually displays the form (following the redirect)
        response_form_get = self.client.get(response_initial_get.url) # Use the redirect URL
        self.assertEqual(response_form_get.status_code, 200,
                         f"Password reset confirm page (after redirect) expected 200, got {response_form_get.status_code}.")
        self.assertTemplateUsed(response_form_get, 'accounts/password_reset_confirm.html')
        
        # 4. Submit new password to the URL that displays the form
        response_set_password = self.client.post(response_initial_get.url, { # Post to the same URL that rendered the form
            'new_password1': 'newStrongPass123!',
            'new_password2': 'newStrongPass123!'
        })
        self.assertRedirects(response_set_password, reverse('accounts:password_reset_complete'))
        
        self.client.logout() 
        login_successful = self.client.login(username=self.active_user_username, password='newStrongPass123!')
        self.assertTrue(login_successful, "Should be able to log in with the new password.")

    def test_static_template_views_render(self):
        pages_to_test_unauthenticated = [
            'accounts:account_activation_sent', 
            'accounts:account_activation_success',
            'accounts:account_activation_invalid', 
            'accounts:resend_activation_email_sent',
            'accounts:password_reset', 
            'accounts:password_reset_done', 
            'accounts:password_reset_complete',
        ]
        for page_name in pages_to_test_unauthenticated:
            response = self.client.get(reverse(page_name))
            self.assertEqual(response.status_code, 200, f"Page {page_name} failed to load. Status: {response.status_code}")
        self.client.login(username=self.active_user_username, password='password123')
        response = self.client.get(reverse('accounts:logout_confirm'))
        self.assertEqual(response.status_code, 200, "Page accounts:logout_confirm failed to load for authenticated user.")
        self.client.logout()
