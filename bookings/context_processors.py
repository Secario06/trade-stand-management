from bookings.models import Booking


def booking_status_context(request):
    """Делает перечисление статусов доступным во всех шаблонах.

    В шаблонах статусы сравниваются с константами
    (BookingStatus.ACTIVE), а не с произвольными строками.
    """
    return {"BookingStatus": Booking.Status}
