from typing import List, Tuple

from django.conf import settings

from models import Booking, Stand, User
from storage import load_bookings, load_stands, load_users


def load_dataset() -> Tuple[List[Stand], List[User], List[Booking]]:
    """Загрузить стенды, пользователей и бронирования из JSON (ПР3)."""
    stands = load_stands(str(settings.DATA_DIR / "stands.json"))
    users = load_users(str(settings.DATA_DIR / "users.json"))
    bookings = load_bookings(
        str(settings.DATA_DIR / "bookings.json"),
        stands,
        users,
    )
    return stands, users, bookings
