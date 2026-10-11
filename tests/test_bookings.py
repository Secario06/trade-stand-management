from models import Booking, Stand, User
from models.bookings import (
    is_stand_available,
    create_booking,
    cancel_booking,
    find_booking_by_id,
    get_booking_status,
)


def _make_stand() -> Stand:
    return Stand(1, "Павильон А", 25.0, "Стандарт")


def _make_user() -> User:
    return User(1, "Иван Петров", "ivan@example.com")


def test_booking_creation():
    stand = _make_stand()
    user = _make_user()
    booking = Booking(1, stand, "2026-10-15", user)
    assert booking.id == 1
    assert booking.stand is stand
    assert booking.user is user
    assert booking.booking_date == "2026-10-15"
    assert booking.is_active()


def test_booking_str():
    stand = _make_stand()
    user = _make_user()
    booking = Booking(1, stand, "2026-10-15", user)
    text = str(booking)
    assert "Павильон А" in text
    assert "Иван Петров" in text
    assert "2026-10-15" in text


def test_booking_cancel():
    stand = _make_stand()
    user = _make_user()
    booking = Booking(1, stand, "2026-10-15", user)
    booking.cancel()
    assert booking.is_cancelled
    assert not booking.is_active()


def test_is_stand_available():
    bookings = []
    stand = _make_stand()
    assert is_stand_available(bookings, stand, "2026-10-15")


def test_create_booking():
    bookings = []
    stand = _make_stand()
    user = _make_user()
    result = create_booking(bookings, stand, "2026-10-15", user)
    assert result is not None
    assert len(bookings) == 1
    assert result.stand is stand
    assert result.user is user


def test_duplicate_booking_forbidden():
    bookings = []
    stand = _make_stand()
    user = _make_user()
    create_booking(bookings, stand, "2026-10-15", user)
    second = create_booking(bookings, stand, "2026-10-15", user)
    assert second is None
    assert len(bookings) == 1


def test_cancelled_booking_frees_stand():
    bookings = []
    stand = _make_stand()
    user = _make_user()
    booking = create_booking(bookings, stand, "2026-10-15", user)
    assert not is_stand_available(bookings, stand, "2026-10-15")
    booking.cancel()
    assert is_stand_available(bookings, stand, "2026-10-15")


def test_cancel_booking():
    bookings = []
    stand = _make_stand()
    user = _make_user()
    create_booking(bookings, stand, "2026-10-15", user)
    assert cancel_booking(bookings, 1) is True
    assert bookings[0].is_cancelled


def test_cancel_nonexistent_booking():
    bookings = []
    assert cancel_booking(bookings, 999) is False


def test_get_booking_status():
    assert get_booking_status(True) == "Стенд доступен для бронирования"
    assert get_booking_status(False) == "Стенд уже занят на эту дату"


def test_find_booking_by_id():
    bookings = []
    booking = create_booking(
        bookings, _make_stand(), "2026-10-15", _make_user()
    )
    assert find_booking_by_id(bookings, booking.id) is booking
    assert find_booking_by_id(bookings, 999) is None
