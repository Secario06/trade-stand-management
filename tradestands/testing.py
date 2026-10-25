import tempfile
from pathlib import Path
from unittest.mock import patch

from db.database import get_connection, init_schema
from db.import_json import import_all


class TempDatabaseMixin:
    """Подставляет временную SQLite-базу с данными из JSON проекта.

    Тесты не зависят от рабочей базы data/tradestands.sqlite и не
    изменяют её.
    """

    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "test.sqlite"
        patcher = patch("db.database.DB_PATH", path)
        patcher.start()
        self.addCleanup(patcher.stop)

        conn = get_connection(create=True)
        try:
            init_schema(conn)
            import_all(conn)
            conn.commit()
        finally:
            conn.close()
