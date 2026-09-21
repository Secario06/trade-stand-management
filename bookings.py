def get_booking_status(is_available: bool) -> str:
    """Возвращает текстовый статус (функция из ПР1)."""
    if is_available:
        return "Стенд доступен для бронирования"
    return "Стенд уже занят на эту дату"


def is_stand_available(
    bookings: list, stand_id: int, booking_date: str
) -> bool:
    """Проверяет, свободен ли стенд на указанную дату."""
    for booking in bookings:
        if booking["stand_id"] == stand_id and \
           booking["date"] == booking_date:
            return False
    return True


def create_booking(
    bookings: list, stand_id: int, booking_date: str
) -> dict | None:
    """Создает бронирование, если стенд свободен."""
    if is_stand_available(bookings, stand_id, booking_date):
        booking_id = max([b["id"] for b in bookings], default=0) + 1
        new_booking = {
            "id": booking_id,
            "stand_id": stand_id,
            "date": booking_date
        }
        bookings.append(new_booking)
        return new_booking
    return None


def cancel_booking(bookings: list, booking_id: int) -> bool:
    """Отменяет бронирование по ID."""
    for i, booking in enumerate(bookings):
        if booking["id"] == booking_id:
            bookings.pop(i)
            return True
    return False
