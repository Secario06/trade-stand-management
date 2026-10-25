from django.urls import path

from . import views


app_name = "stands"

urlpatterns = [
    path("", views.stands, name="list"),
    path("available/", views.available_stands, name="available"),
    path("<int:stand_id>/", views.stand_detail, name="detail"),
]
