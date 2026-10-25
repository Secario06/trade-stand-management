import argparse
import json

from db.database import BASE_DIR, get_connection, init_schema

DATA_DIR = BASE_DIR / "data"
STANDS_FILE = DATA_DIR / "stands.json"
USERS_FILE = DATA_DIR / "users.json"
BOOKINGS_FILE = DATA_DIR / "bookings.json"

# Порядок важен: бронирования ссылаются на стенды и арендаторов.
TABLES = ("stands", "users", "bookings")


def load_json(filename):
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def import_stands(conn):
    stands = load_json(STANDS_FILE)
    conn.executemany(
        """
        INSERT INTO stands (id, name, area, stand_type)
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                stand["id"],
                stand["name"],
                stand["area"],
                stand["type"],
            )
            for stand in stands
        ],
    )


def import_users(conn):
    users = load_json(USERS_FILE)
    conn.executemany(
        """
        INSERT INTO users (id, name, email)
        VALUES (?, ?, ?)
        """,
        [
            (
                user["id"],
                user["name"],
                user["email"],
            )
            for user in users
        ],
    )


def import_bookings(conn):
    bookings = load_json(BOOKINGS_FILE)
    conn.executemany(
        """
        INSERT INTO bookings (
            id, stand_id, user_id, booking_date, is_cancelled
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                booking["id"],
                booking["stand_id"],
                booking["user_id"],
                booking["date"],
                int(booking.get("is_cancelled", False)),
            )
            for booking in bookings
        ],
    )


def count_rows(conn):
    """Количество записей в каждой таблице."""
    return {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in TABLES
    }


def clear_tables(conn):
    """Очистить таблицы (сначала зависимые)."""
    for table in reversed(TABLES):
        conn.execute(f"DELETE FROM {table}")


def import_all(conn):
    """Перенести все JSON-файлы в таблицы в правильном порядке."""
    import_stands(conn)
    import_users(conn)
    import_bookings(conn)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Перенос данных из JSON-файлов в SQLite"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="очистить таблицы перед импортом",
    )
    args = parser.parse_args(argv)

    conn = get_connection(create=True)
    try:
        init_schema(conn)
        if args.reset:
            clear_tables(conn)
        elif any(count_rows(conn).values()):
            print(
                "В базе уже есть данные, импорт пропущен. "
                "Для повторного импорта: python -m db.import_json --reset"
            )
            return 1
        import_all(conn)
        conn.commit()
        counts = count_rows(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("Импорт выполнен:", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
