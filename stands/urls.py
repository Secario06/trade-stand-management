from django.urls import path

from . import views


app_name = "stands"

urlpatterns = [
    path("", views.stands, name="list"),
    path("available/", views.available_stands, name="available"),
    # Страница стенда открывается по текстовому идентификатору (slug).
    path("<slug:slug>/", views.stand_detail, name="detail"),
]
