from django.urls import path
from .views import HomeView

app_name = 'accounts'  # Namespace for URL names

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', HomeView.as_view(), name='login'),  # Temporary
    path('signup/', HomeView.as_view(), name='signup'),  # Temporary
]