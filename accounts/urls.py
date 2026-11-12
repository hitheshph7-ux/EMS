from django.urls import path

from .views import (
    LoginView,
    RefreshTokenView,
    LogoutView,
    PasswordChangeView,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("refresh", RefreshTokenView.as_view(), name="refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("password/change", PasswordChangeView.as_view(), name="password-change"),
]
