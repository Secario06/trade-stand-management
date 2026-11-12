import sqlite3
from contextlib import closing
from pathlib import Path

# Корень проекта: скрипт лежит в подкаталоге db.
BASE_DIR = Path(__file__).resolve().parent.parent

# Исходная база, созданная в ПР7.
SOURCE_DB = BASE_DIR / "data" / "tradestands.sqlite"


def main():
    """Вывести таблицы, столбцы и число записей исходной базы."""
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"Исходная база не найдена: {SOURCE_DB}")

    # Только запросы на чтение: исходная база не изменяется.
    with closing(sqlite3.connect(SOURCE_DB)) as connection:
        connection.row_factory = sqlite3.Row

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        for (table_name,) in tables:
            print(f"\nТаблица: {table_name}")
            columns = connection.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
            print("Столбцы:")
            for column in columns:
                print(
                    f"  имя={column['name']}, "
                    f"тип={column['type']}, "
                    f"NOT NULL={column['notnull']}, "
                    f"PRIMARY KEY={column['pk']}"
                )
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            print(f"Количество записей: {count}")

        # Проверки целостности перед переносом.
        orphans = connection.execute(
            """
            SELECT COUNT(*) FROM bookings
            WHERE stand_id NOT IN (SELECT id FROM stands)
               OR user_id NOT IN (SELECT id FROM users)
            """
        ).fetchone()[0]
        print(f"\nБронирований со ссылкой на несуществующие записи: "
              f"{orphans}")
        flags = connection.execute(
            "SELECT DISTINCT is_cancelled FROM bookings"
        ).fetchall()
        print("Значения is_cancelled:", sorted(row[0] for row in flags))


if __name__ == "__main__":
    main()
