# accounts/views.py

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from .forms import CustomUserCreationForm

class HomeView(TemplateView):
    """
    View for the project's homepage.
    Assumes this view is mapped to the root URL ('/') in the main urls.py.
    """
    template_name = 'accounts/home.html' # Assuming home.html is in project-level templates or similar

class SignUpView(CreateView):
    """
    View for user registration.
    Uses CustomUserCreationForm to create new users.
    Redirects to the login page upon successful registration.
    """
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')

class CustomLoginView(LoginView):
    """
    View for user login.
    Inherits from Django's built-in LoginView.
    Uses the specified template for the login form.
    Redirects after successful login is configured via settings.LOGIN_REDIRECT_URL.
    """
    template_name = 'accounts/login.html'



class CustomLogoutView(LogoutView):
    """
    View for user logout.
    Inherits from Django's built-in LogoutView.
    Redirects to the URL specified by next_page after successful logout.
    settings.LOGOUT_REDIRECT_URL can also be used if next_page is not set.
    """
    next_page = reverse_lazy('home') # Redirect to the homepage after logout