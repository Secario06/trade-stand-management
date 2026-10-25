import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "tradestands.sqlite"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"


def _lower(value):
    """Перевод в нижний регистр с поддержкой кириллицы."""
    return value.lower() if isinstance(value, str) else value


def get_connection(create=False):
    """Подключиться к базе SQLite проекта.

    По умолчанию отсутствующий файл базы – ошибка: иначе sqlite3
    молча создал бы пустую базу без таблиц. Файл создаётся только
    при create=True (скрипт импорта).
    """
    if not create and not Path(DB_PATH).exists():
        raise FileNotFoundError(
            f"База данных {DB_PATH} не найдена. "
            "Создайте её командой: python -m db.import_json"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    # Встроенные lower()/LIKE в SQLite не учитывают регистр кириллицы,
    # поэтому lower() переопределяется Python-функцией.
    conn.create_function("lower", 1, _lower, deterministic=True)
    return conn


@contextmanager
def open_connection():
    """Соединение для веб-представлений: поля по именам и автозакрытие."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn):
    """Создать таблицы из sql/schema.sql (повторный запуск безопасен)."""
    with open(SCHEMA_PATH, encoding="utf-8") as file:
        conn.executescript(file.read())
