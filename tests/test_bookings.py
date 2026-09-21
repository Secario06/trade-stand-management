from bookings import is_stand_available, create_booking, get_booking_status


def test_is_stand_available():
    bookings = []
    assert is_stand_available(bookings, 1, "2026-10-15") is True


def test_create_booking():
    bookings = []
    result = create_booking(bookings, 1, "2026-10-15")
    assert result is not None
    assert len(bookings) == 1
    assert bookings[0]["stand_id"] == 1


def test_duplicate_booking_forbidden():
    bookings = []
    create_booking(bookings, 1, "2026-10-15")
    second_attempt = create_booking(bookings, 1, "2026-10-15")
    assert second_attempt is None
    assert len(bookings) == 1


def test_get_booking_status():
    assert get_booking_status(True) == "Стенд доступен для бронирования"
    assert get_booking_status(False) == "Стенд уже занят на эту дату"
