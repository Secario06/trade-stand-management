import json
import os
from typing import List

from models import Booking, Stand, User
from models.stands import find_stand_by_id
from models.users import find_user_by_id


def _ensure_dir(filename: str) -> None:
    """Создать директорию для файла, если её нет."""
    dirname = os.path.dirname(filename)
    if dirname:
        os.makedirs(dirname, exist_ok=True)


def load_stands(filename: str) -> List[Stand]:
    """Загрузить стенды из JSON и преобразовать в объекты."""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            data = list(data.values())
        return [Stand.from_data(item) for item in data]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Ошибка загрузки стендов: {e}")
        return []


def save_stands(filename: str, stands: List[Stand]) -> None:
    """Сохранить объекты Stand в JSON."""
    _ensure_dir(filename)
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                [s.to_data() for s in stands],
                file,
                ensure_ascii=False,
                indent=4,
            )
    except OSError as e:
        print(f"Ошибка сохранения стендов: {e}")


def load_users(filename: str) -> List[User]:
    """Загрузить пользователей из JSON."""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [User.from_data(item) for item in data]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Ошибка загрузки пользователей: {e}")
        return []


def save_users(filename: str, users: List[User]) -> None:
    """Сохранить объекты User в JSON."""
    _ensure_dir(filename)
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                [u.to_data() for u in users],
                file,
                ensure_ascii=False,
                indent=4,
            )
    except OSError as e:
        print(f"Ошибка сохранения пользователей: {e}")


def load_bookings(
    filename: str,
    stands: List[Stand],
    users: List[User],
) -> List[Booking]:
    """Загрузить брони и восстановить связи с Room и User."""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
        bookings: List[Booking] = []
        for item in data:
            stand = find_stand_by_id(stands, item["stand_id"])
            user = find_user_by_id(users, item.get("user_id", 0))
            if stand is None or user is None:
                continue
            booking = Booking(
                booking_id=item["id"],
                stand=stand,
                booking_date=item["date"],
                user=user,
            )
            booking.is_cancelled = item.get("is_cancelled", False)
            bookings.append(booking)
        return bookings
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Ошибка загрузки бронирований: {e}")
        return []


def save_bookings(
    filename: str, bookings: List[Booking]
) -> None:
    """Сохранить объекты Booking в JSON (с ID связанных)."""
    _ensure_dir(filename)
    try:
        with open(filename, "w", encoding="utf-8") as file:
            data = [
                {
                    "id": b.id,
                    "stand_id": b.stand.id,
                    "date": b.booking_date,
                    "user_id": b.user.id,
                    "is_cancelled": b.is_cancelled,
                }
                for b in bookings
            ]
            json.dump(data, file, ensure_ascii=False, indent=4)
    except OSError as e:
        print(f"Ошибка сохранения бронирований: {e}")
