from typing import List, Optional

from .stands import Stand
from .users import User


class Booking:
    """Бронирование торгового стенда."""

    def __init__(
        self,
        booking_id: int,
        stand: Stand,
        booking_date: str,
        user: User,
    ) -> None:
        """Создать объект бронирования."""
        self.id = booking_id
        self.stand = stand
        self.booking_date = booking_date
        self.user = user
        self.is_cancelled = False

    def cancel(self) -> None:
        """Отменить бронирование."""
        self.is_cancelled = True

    def is_active(self) -> bool:
        """Проверить, активно ли бронирование."""
        return not self.is_cancelled

    def __str__(self) -> str:
        """Вернуть строковое представление бронирования."""
        status = "отменено" if self.is_cancelled else "активно"
        return (
            f"Бронь №{self.id} | Стенд: {self.stand.name} | "
            f"Дата: {self.booking_date} | "
            f"Арендатор: {self.user.name} | Статус: {status}"
        )


def is_stand_available(
    bookings: List[Booking],
    stand: Stand,
    booking_date: str,
) -> bool:
    """Проверить, свободен ли стенд на указанную дату."""
    for booking in bookings:
        if (
            booking.stand.id == stand.id
            and booking.booking_date == booking_date
            and booking.is_active()
        ):
            return False
    return True


def create_booking(
    bookings: List[Booking],
    stand: Stand,
    booking_date: str,
    user: User,
) -> Optional[Booking]:
    """Создать бронирование, если стенд свободен."""
    if not is_stand_available(bookings, stand, booking_date):
        return None
    booking_id = max([b.id for b in bookings], default=0) + 1
    booking = Booking(booking_id, stand, booking_date, user)
    bookings.append(booking)
    return booking


def cancel_booking(bookings: List[Booking], booking_id: int) -> bool:
    """Отменить бронирование по идентификатору."""
    for booking in bookings:
        if booking.id == booking_id:
            booking.cancel()
            return True
    return False


def get_booking_status(is_available: bool) -> str:
    """Вернуть текстовый статус доступности стенда."""
    if is_available:
        return "Стенд доступен для бронирования"
    return "Стенд уже занят на эту дату"
