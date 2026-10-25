import json
import re
import sqlite3
from pathlib import Path

import pytest

from db import database, import_json
from db.database import get_connection, init_schema

BASE_DIR = Path(__file__).resolve().parent.parent
QUERIES_FILE = BASE_DIR / "sql" / "queries.sql"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Пустой файл базы во временном каталоге."""
    path = tmp_path / "test.sqlite"
    monkeypatch.setattr(database, "DB_PATH", path)
    return path


@pytest.fixture
def conn(db_path):
    """Соединение с базой, созданной по схеме и заполненной из JSON."""
    connection = get_connection(create=True)
    init_schema(connection)
    import_json.import_all(connection)
    connection.commit()
    yield connection
    connection.close()


def _json_len(name):
    with open(BASE_DIR / "data" / name, encoding="utf-8") as file:
        return len(json.load(file))


def _queries():
    """Разобрать sql/queries.sql на пронумерованные запросы."""
    text = QUERIES_FILE.read_text(encoding="utf-8")
    result = {}
    for block in re.split(r"\n(?=-- \d+\. )", text):
        match = re.match(r"-- (\d+)\. ", block)
        if not match:
            continue
        lines = []
        for line in block.splitlines():
            if line.startswith("-- ---"):
                break
            if not line.startswith("--"):
                lines.append(line)
        result[int(match.group(1))] = "\n".join(lines).strip()
    return result


# ---------- схема и подключение ----------


def test_schema_creates_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {row[0] for row in rows}
    assert {"stands", "users", "bookings"} <= names


def test_schema_has_foreign_keys(conn):
    keys = conn.execute("PRAGMA foreign_key_list(bookings)").fetchall()
    assert {row[2] for row in keys} == {"stands", "users"}


def test_schema_can_be_applied_twice(conn):
    init_schema(conn)
    init_schema(conn)


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO bookings "
            "(stand_id, user_id, booking_date) VALUES (?, ?, ?)",
            [999, 1, "2026-12-01"],
        )


def test_area_must_be_positive(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO stands (name, area, stand_type) VALUES (?, ?, ?)",
            ["Нулевой", 0, "Стандарт"],
        )


def test_one_active_booking_per_stand_and_date(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO bookings (stand_id, user_id, booking_date) "
            "VALUES (1, 2, '2026-10-15')"
        )
    # Отменённое бронирование на занятую дату допустимо.
    conn.execute(
        "INSERT INTO bookings "
        "(stand_id, user_id, booking_date, is_cancelled) "
        "VALUES (1, 2, '2026-10-15', 1)"
    )


def test_missing_database_is_an_error(db_path):
    assert not db_path.exists()
    with pytest.raises(FileNotFoundError):
        get_connection()
    assert not db_path.exists()


def test_lower_supports_cyrillic(conn):
    value = conn.execute("SELECT lower('ПАВИЛЬОН')").fetchone()[0]
    assert value == "павильон"


# ---------- импорт из JSON ----------


def test_import_counts_match_json(conn):
    counts = import_json.count_rows(conn)
    assert counts["stands"] == _json_len("stands.json")
    assert counts["users"] == _json_len("users.json")
    assert counts["bookings"] == _json_len("bookings.json")


def test_import_converts_values(conn):
    stand = conn.execute("SELECT * FROM stands WHERE id = 1").fetchone()
    assert stand == (1, "Павильон А", 25.0, "Стандарт")
    flags = {
        row[0]: row[1]
        for row in conn.execute("SELECT id, is_cancelled FROM bookings")
    }
    assert flags[3] == 1
    assert flags[1] == 0


def test_repeated_import_is_refused(conn):
    assert import_json.main([]) == 1
    assert import_json.count_rows(conn)["stands"] == _json_len("stands.json")


def test_import_reset_reloads_data(conn):
    conn.execute("UPDATE stands SET name = 'Изменён' WHERE id = 1")
    conn.commit()
    assert import_json.main(["--reset"]) == 0
    name = conn.execute("SELECT name FROM stands WHERE id = 1").fetchone()[0]
    assert name == "Павильон А"


def test_first_import_creates_database(db_path):
    assert not db_path.exists()
    assert import_json.main([]) == 0
    assert db_path.exists()


# ---------- sql/queries.sql ----------


def test_queries_file_has_enough_queries():
    queries = _queries()
    assert len(queries) >= 10
    text = "\n".join(queries.values())
    assert text.count("JOIN") >= 2
    assert text.count("GROUP BY") >= 2
    assert text.count("COUNT(") >= 2
    assert text.count("WHERE") >= 2
    assert "HAVING" in text


def test_every_query_runs(conn):
    for number, sql in _queries().items():
        rows = conn.execute(sql).fetchall()
        assert isinstance(rows, list), number


def test_query_results(conn):
    queries = _queries()
    run = lambda n: conn.execute(queries[n]).fetchall()  # noqa: E731

    assert [row[1] for row in run(1)] == [
        "Павильон А",
        "Павильон Б",
        "Премиум-зона",
        "Центральный остров",
    ]
    assert [row[1] for row in run(4)] == [
        "Павильон А",
        "Центральный остров",
        "Премиум-зона",
    ]
    assert [row[0] for row in run(6)] == [1, 2, 4, 5]
    assert [row[1] for row in run(13)] == [
        "Павильон Б",
        "Центральный остров",
    ]
    assert run(14)[0][0] == 4
    assert run(15)[0][0] == 1
    assert dict(run(17)) == {
        "Павильон А": 2,
        "Премиум-зона": 2,
        "Павильон Б": 0,
        "Центральный остров": 0,
    }
    assert dict(run(20)) == {"Павильон А": 2, "Премиум-зона": 2}


def test_parameter_is_not_interpreted_as_sql(conn):
    payload = "' OR 1=1; DROP TABLE stands; --"
    rows = conn.execute(
        "SELECT id FROM stands WHERE name = ?", [payload]
    ).fetchall()
    assert rows == []
    assert conn.execute("SELECT COUNT(*) FROM stands").fetchone()[0] == 4
