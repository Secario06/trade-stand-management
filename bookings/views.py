from django.shortcuts import render

from models.bookings import find_booking_by_id
from tradestands.dataset import load_dataset


def bookings(request):
    """Страница /bookings/: список бронирований из data/bookings.json."""
    _, _, bookings_list = load_dataset()

    context = {
        "bookings": bookings_list,
    }

    return render(request, "bookings/booking_list.html", context)


def booking_detail(request, booking_id):
    """Страница /bookings/<id>/: информация о бронировании."""
    _, _, bookings_list = load_dataset()
    booking = find_booking_by_id(bookings_list, booking_id)

    context = {
        "booking": booking,
    }

    return render(
        request,
        "bookings/booking_detail.html",
        context,
        status=404 if booking is None else 200,
    )
