from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape

from homepage.views import page
from models.bookings import Booking, find_booking_by_id
from tradestands.dataset import load_dataset


def _status(booking: Booking) -> tuple:
    """Вернуть текст статуса и класс бейджа Bootstrap."""
    if booking.is_cancelled:
        return "отменено", "bg-secondary"
    return "активно", "bg-success"


def bookings(request):
    """Страница /bookings/: список бронирований из data/bookings.json."""
    _, _, bookings_list = load_dataset()

    items = ""
    for booking in bookings_list:
        status, badge = _status(booking)
        url = reverse("booking_detail", args=[booking.id])
        items += f"""
        <li class="list-group-item d-flex justify-content-between">
            <a href="{url}">
                {escape(booking.stand.name)} – {escape(booking.booking_date)}
            </a>
            <span class="badge {badge}">{status}</span>
        </li>
        """
    if not items:
        items = '<li class="list-group-item">Бронирований пока нет.</li>'

    content = f"""
    <h1>Бронирования</h1>
    <ul class="list-group">{items}</ul>
    """
    return HttpResponse(page("Торговые стенды – бронирования", content))


def booking_detail(request, booking_id):
    """Страница /bookings/<id>/: информация о бронировании."""
    _, _, bookings_list = load_dataset()

    booking = find_booking_by_id(bookings_list, booking_id)
    if booking is None:
        content = f"""
        <h1 class="text-danger">Бронирование не найдено</h1>
        <a href="{reverse("bookings")}"
           class="btn btn-outline-secondary">
            ← к списку бронирований
        </a>
        """
        return HttpResponse(
            page("Бронирование не найдено", content),
            status=404,
        )

    status, badge = _status(booking)
    stand_url = reverse("stand_detail", args=[booking.stand.id])
    content = f"""
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">Бронирование №{booking.id}</h5>
            <p class="card-text">
                Стенд: <a href="{stand_url}">{escape(booking.stand.name)}</a>
            </p>
            <p class="card-text">
                Дата: {escape(booking.booking_date)}
            </p>
            <p class="card-text">
                Арендатор: {escape(booking.user.name)}
                ({escape(booking.user.email)})
            </p>
            <p class="card-text">
                Статус: <span class="badge {badge}">{status}</span>
            </p>
            <a href="{reverse("bookings")}"
               class="btn btn-outline-secondary">
                ← к списку бронирований
            </a>
        </div>
    </div>
    """
    return HttpResponse(
        page(f"Бронирование №{booking.id}", content),
        status=200,
    )
