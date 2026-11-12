"""Перенос данных из базы ПР7 (SQLite) в таблицы Django ORM.

Исходная база data/tradestands.sqlite только читается и не изменяется.
Данные записываются в базу, настроенную в DATABASES (db.sqlite3), после
применения миграций.

Запуск из корня проекта:
    python db/import_sqlite_to_orm.py
"""
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

import django
from django.db import transaction

# Корень проекта: скрипт находится в подкаталоге db.
BASE_DIR = Path(__file__).resolve().parent.parent

# Корень проекта добавляется в пути поиска модулей, чтобы найти
# пакет настроек при запуске скрипта из любого каталога.
sys.path.insert(0, str(BASE_DIR))

# Исходная база данных, созданная в ПР7.
SOURCE_DB = BASE_DIR / "data" / "tradestands.sqlite"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tradestands.settings")
django.setup()

# Модели импортируются только после django.setup().
from bookings.models import Booking  # noqa: E402
from stands.models import Stand  # noqa: E402
from users.models import User  # noqa: E402


def read_source(source_db):
    """Прочитать стенды, арендаторов и бронирования из исходной базы."""
    if not Path(source_db).exists():
        raise FileNotFoundError(f"Исходная база не найдена: {source_db}")

    # Режим «только чтение»: исходная база гарантированно не изменится.
    uri = Path(source_db).resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.row_factory = sqlite3.Row
        stands = connection.execute(
            "SELECT id, name, area, stand_type FROM stands ORDER BY id"
        ).fetchall()
        users = connection.execute(
            "SELECT id, name, email FROM users ORDER BY id"
        ).fetchall()
        bookings = connection.execute(
            """
            SELECT id, stand_id, user_id, booking_date, is_cancelled
            FROM bookings
            ORDER BY id
            """
        ).fetchall()
    finally:
        # Соединение закрывается явно (with только фиксирует транзакцию).
        connection.close()
    return stands, users, bookings


def main(source_db=SOURCE_DB, verbose=True):
    """Перенести данные в ORM одной транзакцией."""
    stands, users, bookings = read_source(source_db)

    # При ошибке все изменения внутри транзакции откатываются.
    with transaction.atomic():
        # Сначала независимые сущности, затем бронирования,
        # которые ссылаются на них внешними ключами.
        for row in stands:
            Stand.objects.update_or_create(
                pk=row["id"],  # исходный идентификатор сохраняется
                defaults={
                    "name": row["name"],
                    "area": row["area"],
                    "stand_type": row["stand_type"],
                },
            )

        for row in users:
            User.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "name": row["name"],
                    "email": row["email"],
                },
            )

        for row in bookings:
            Booking.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "stand_id": row["stand_id"],
                    "user_id": row["user_id"],
                    # Строка ГГГГ-ММ-ДД превращается в объект date.
                    "booking_date": date.fromisoformat(
                        row["booking_date"]
                    ),
                    # Булев признак исходной базы превращается в статус.
                    "status": (
                        Booking.Status.CANCELLED
                        if row["is_cancelled"]
                        else Booking.Status.ACTIVE
                    ),
                },
            )

    counts = {
        "stands": Stand.objects.count(),
        "users": User.objects.count(),
        "bookings": Booking.objects.count(),
    }
    if verbose:
        print("Перенос данных завершён.")
        print(f"Стендов: {counts['stands']}")
        print(f"Арендаторов: {counts['users']}")
        print(f"Бронирований: {counts['bookings']}")
    return counts


if __name__ == "__main__":
    main()
