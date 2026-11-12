from django.contrib import admin
from django.urls import include, include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from accounts.views import CurrentUserView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("EMS.urls")),
    # Authentication APIs
    path("api/auth/", include("accounts.urls")),

    # Current user profile API (Module 1 guide)
    path("api/me", CurrentUserView.as_view(), name="current-user"),

    # Society and master-data APIs
    path("api/", include("societies.urls")),

    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

