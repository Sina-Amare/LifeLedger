# accounts/urls.py
from django.urls import path
from .views import SignUpView, CustomLoginView, CustomLogoutView, HomeView

app_name = 'accounts'  # Namespace for these app-specific URL names

urlpatterns = [
    # URL pattern for the signup page
    path('signup/', SignUpView.as_view(), name='signup'),

    # URL pattern for the login page
    path('login/', CustomLoginView.as_view(), name='login'),

    # URL pattern for the logout action
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    path('', HomeView.as_view(), name='home'),
]