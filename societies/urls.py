
from django.urls import path

from .views import (
    DistrictListView,
    SocietyTypeListView,
    SocietyListCreateView,
    SocietyDetailView,
)


urlpatterns = [
    path("masters/districts", DistrictListView.as_view(), name="district-list"),
    path("masters/society-types", SocietyTypeListView.as_view(), name="society-type-list"),
    path("societies", SocietyListCreateView.as_view(), name="society-list-create"),
    path("societies/<int:pk>", SocietyDetailView.as_view(), name="society-detail"),
]
