from django.urls import path

from . import views


urlpatterns = [
    path("", views.stands, name="stands"),
    path("<int:stand_id>/", views.stand_detail, name="stand_detail"),
]
