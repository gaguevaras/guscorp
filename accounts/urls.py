from django.urls import path
from knox import views as knox_views
from .views import LoginView

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='knox_login'),
    path('auth/logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    # Use Python comments, not JavaScript style
] 