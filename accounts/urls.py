from django.urls import path
from knox import views as knox_views
from .views import LoginView, UserProfileView

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='knox_login'),
    path('auth/logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
    # Use Python comments, not JavaScript style
] 