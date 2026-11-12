import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

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


class AppConfigTests(TestCase):
    def test_apps_have_russian_names(self):
        self.assertEqual(
            apps.get_app_config("stands").verbose_name, "Торговые стенды"
        )
        self.assertEqual(
            apps.get_app_config("users").verbose_name, "Арендаторы"
        )
        self.assertEqual(
            apps.get_app_config("bookings").verbose_name, "Бронирования"
        )

    def test_models_have_russian_names(self):
        self.assertEqual(Stand._meta.verbose_name_plural, "Стенды")
        self.assertEqual(User._meta.verbose_name, "Арендатор")
        self.assertEqual(
            Booking._meta.get_field("status").verbose_name,
            "Статус бронирования",
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

    def test_all_three_statuses_are_present(self):
        statuses = set(Booking.objects.values_list("status", flat=True))
        self.assertEqual(statuses, {"active", "cancelled", "completed"})


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

    def test_boolean_flag_becomes_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            import_to_orm(source_db=self.make_source(tmp), verbose=False)
        self.assertEqual(
            Booking.objects.get(pk=3).status, Booking.Status.CANCELLED
        )
        self.assertEqual(
            Booking.objects.get(pk=1).status, Booking.Status.ACTIVE
        )

    def test_imported_stands_get_slugs(self):
        with tempfile.TemporaryDirectory() as tmp:
            import_to_orm(source_db=self.make_source(tmp), verbose=False)
        self.assertEqual(Stand.objects.get(pk=1).slug, "pavilon-a-1")

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


class StatusDataMigrationTests(TransactionTestCase):
    """Перенос is_cancelled → status при миграции bookings 0002 → 0003."""

    # Стенды откатываются к начальной схеме (без slug), как на момент
    # создания поля status.
    migrate_from = [
        ("bookings", "0002_booking_status"),
        ("stands", "0001_initial"),
    ]
    migrate_to = [("bookings", "0003_migrate_booking_statuses")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        self.old_apps = executor.loader.project_state(
            self.migrate_from
        ).apps

    def tearDown(self):
        # Возвращаем базу к актуальной схеме для следующих тестов.
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_old_flags_are_converted_to_statuses(self):
        old_stand = self.old_apps.get_model("stands", "Stand")
        old_user = self.old_apps.get_model("users", "User")
        old_booking = self.old_apps.get_model("bookings", "Booking")

        # На этом шаге истории миграций у стенда ещё нет поля slug.
        stand = old_stand.objects.create(
            name="Тест", area=10, stand_type="Остров"
        )
        user = old_user.objects.create(name="Тест", email="t@example.com")
        active = old_booking.objects.create(
            stand=stand,
            user=user,
            booking_date="2027-01-01",
            is_cancelled=False,
        )
        cancelled = old_booking.objects.create(
            stand=stand,
            user=user,
            booking_date="2027-01-02",
            is_cancelled=True,
        )
        # До миграции данных у всех стоит значение по умолчанию.
        self.assertEqual(active.status, "active")
        self.assertEqual(cancelled.status, "active")

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        new_booking = new_apps.get_model("bookings", "Booking")

        self.assertEqual(
            new_booking.objects.get(pk=active.pk).status, "active"
        )
        self.assertEqual(
            new_booking.objects.get(pk=cancelled.pk).status, "cancelled"
        )
