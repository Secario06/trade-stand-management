from django.urls import path

from . import views


app_name = "bookings"

urlpatterns = [
    path("", views.booking_list, name="bookings"),
    path("statistics/", views.statistics, name="statistics"),
    # Статический маршрут create/ расположен до маршрутов с параметрами.
    path("create/", views.booking_create, name="booking_create"),
    path("<int:booking_id>/", views.booking_detail, name="detail"),
    path(
        "<int:booking_id>/edit/",
        views.booking_update,
        name="booking_update",
    ),
    path(
        "<int:booking_id>/cancel/",
        views.booking_cancel,
        name="booking_cancel",
    ),
]
