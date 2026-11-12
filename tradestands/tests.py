import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from bookings.models import Booking
from db import database, import_json
from db.import_sqlite_to_orm import main as import_to_orm
from stands.models import Stand
from users.models import User


class MigrationsTests(TestCase):
    def test_models_have_no_pending_migrations(self):
        # --check завершается ошибкой, если модели изменены без миграции.
        call_command(
            "makemigrations", check=True, dry_run=True, verbosity=0
        )


class FixtureTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_fixture_loads_complete_consistent_data(self):
        self.assertEqual(Stand.objects.count(), 4)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(Booking.objects.count(), 9)
        # Каждое бронирование связано с существующими стендом и арендатором.
        for booking in Booking.objects.select_related("stand", "user"):
            self.assertTrue(booking.stand.name)
            self.assertTrue(booking.user.name)


class ImportFromSqliteTests(TestCase):
    """Перенос данных из базы ПР7 (SQLite) в таблицы ORM."""

    def make_source(self, tmp):
        path = Path(tmp) / "source.sqlite"
        with patch.object(database, "DB_PATH", path):
            conn = database.get_connection(create=True)
            try:
                database.init_schema(conn)
                import_json.import_all(conn)
                conn.commit()
            finally:
                conn.close()
        return path

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def test_import_preserves_ids_links_and_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_source(tmp)
            counts = import_to_orm(source_db=source, verbose=False)

        self.assertEqual(counts, {"stands": 4, "users": 3, "bookings": 5})
        booking = Booking.objects.select_related("stand", "user").get(pk=3)
        self.assertEqual(booking.stand.name, "Павильон А")
        self.assertEqual(booking.user.name, "Анна Смирнова")
        self.assertEqual(booking.booking_date.isoformat(), "2026-10-20")
        self.assertTrue(booking.is_cancelled)
        self.assertFalse(Booking.objects.get(pk=1).is_cancelled)

    def test_import_is_repeatable_and_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_source(tmp)
            import_to_orm(source_db=source, verbose=False)
            Stand.objects.filter(pk=1).update(name="Изменён")
            counts = import_to_orm(source_db=source, verbose=False)

        self.assertEqual(counts["stands"], 4)
        self.assertEqual(Stand.objects.get(pk=1).name, "Павильон А")

    def test_source_database_is_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_source(tmp)
            before = self.digest(source)
            import_to_orm(source_db=source, verbose=False)
            after = self.digest(source)
        self.assertEqual(before, after)

    def test_missing_source_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            import_to_orm(source_db=Path("нет-такой-базы.sqlite"))
