from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from stands.models import Stand


class StandModelTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_str_and_default_ordering(self):
        names = [str(stand) for stand in Stand.objects.all()]
        self.assertEqual(
            names,
            [
                "Павильон А",
                "Павильон Б",
                "Премиум-зона",
                "Центральный остров",
            ],
        )

    def test_create_read_update_delete(self):
        stand = Stand.objects.create(
            name="Тестовый стенд", area=12.5, stand_type="Остров"
        )
        self.assertEqual(Stand.objects.get(pk=stand.pk).area, 12.5)

        stand.area = 20.0
        self.assertEqual(Stand.objects.get(pk=stand.pk).area, 12.5)
        stand.save()
        self.assertEqual(Stand.objects.get(pk=stand.pk).area, 20.0)

        stand.delete()
        self.assertFalse(Stand.objects.filter(pk=stand.pk).exists())

    def test_default_type(self):
        stand = Stand.objects.create(name="Без типа", area=5)
        self.assertEqual(stand.stand_type, Stand.StandType.STANDARD)

    def test_area_validator(self):
        stand = Stand(name="Нулевой", area=0, stand_type="Остров")
        with self.assertRaises(ValidationError) as ctx:
            stand.full_clean()
        self.assertIn("area", ctx.exception.message_dict)

    def test_area_check_constraint_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Stand.objects.create(name="Нулевой", area=0)

    def test_choices_are_validated(self):
        stand = Stand(name="Тест", area=5, stand_type="Неизвестный")
        with self.assertRaises(ValidationError) as ctx:
            stand.full_clean()
        self.assertIn("stand_type", ctx.exception.message_dict)

    def test_protected_from_deletion_when_booked(self):
        stand = Stand.objects.get(pk=1)
        with self.assertRaises(ProtectedError):
            stand.delete()

    def test_unused_stand_can_be_deleted(self):
        stand = Stand.objects.create(name="Лишний", area=3)
        stand.delete()

    def test_reverse_relation(self):
        stand = Stand.objects.get(pk=1)
        self.assertEqual(stand.bookings.count(), 4)
        self.assertEqual(
            stand.bookings.filter(is_cancelled=False).count(), 3
        )

    def test_is_available_on(self):
        stand = Stand.objects.get(pk=1)
        self.assertFalse(stand.is_available_on(date(2026, 10, 15)))
        # Отменённая бронь стенд не блокирует.
        self.assertTrue(stand.is_available_on(date(2026, 10, 20)))
        self.assertTrue(stand.is_available_on(date(2030, 1, 1)))


class UnicodeSearchTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_icontains_ignores_cyrillic_case(self):
        for query in ("павильон", "ПАВИЛЬОН", "Павильон"):
            names = list(
                Stand.objects.filter(name__icontains=query)
                .values_list("name", flat=True)
            )
            self.assertEqual(names, ["Павильон А", "Павильон Б"], query)

    def test_istartswith_and_iexact(self):
        self.assertEqual(
            Stand.objects.filter(name__istartswith="премиум").count(), 1
        )
        self.assertEqual(
            Stand.objects.filter(name__iexact="павильон а").count(), 1
        )

    def test_wildcards_are_escaped(self):
        self.assertEqual(Stand.objects.filter(name__icontains="%").count(), 0)
        self.assertEqual(Stand.objects.filter(name__icontains="_").count(), 0)


class StandListViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def names(self, response):
        return [stand.name for stand in response.context["stands"]]

    def test_list(self):
        response = self.client.get("/stands/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/stand_list.html")
        self.assertTemplateUsed(response, "stands/includes/stand_card.html")
        self.assertEqual(len(self.names(response)), 4)
        self.assertContains(response, "Найдено стендов: 4")
        self.assertContains(response, 'href="/stands/1/"')

    def test_context_contains_model_objects(self):
        stand = self.client.get("/stands/").context["stands"][0]
        self.assertIsInstance(stand, Stand)

    def test_search_by_name(self):
        response = self.client.get("/stands/?q=павильон")
        self.assertEqual(self.names(response), ["Павильон А", "Павильон Б"])

    def test_filter_by_min_area(self):
        response = self.client.get("/stands/?min_area=30")
        self.assertEqual(
            self.names(response), ["Премиум-зона", "Центральный остров"]
        )

    def test_filter_accepts_comma(self):
        response = self.client.get("/stands/?min_area=36,0")
        self.assertEqual(len(self.names(response)), 2)

    def test_search_and_filter_combined(self):
        response = self.client.get("/stands/?q=павильон&min_area=20")
        self.assertEqual(self.names(response), ["Павильон А"])

    def test_invalid_min_area(self):
        response = self.client.get("/stands/?min_area=abc")
        self.assertContains(response, "должна быть числом")
        self.assertEqual(len(self.names(response)), 4)

    def test_empty_result(self):
        response = self.client.get("/stands/?q=несуществующий")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Стенды не найдены.")

    def test_sql_injection_text_is_harmless(self):
        response = self.client.get("/stands/", {"q": "'; DROP TABLE x; --"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.names(response)), 0)
        self.assertEqual(Stand.objects.count(), 4)


class StandDetailViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_detail(self):
        response = self.client.get("/stands/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/stand_detail.html")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Площадь")
        self.assertIsInstance(response.context["stand"], Stand)

    def test_history_through_reverse_relation(self):
        response = self.client.get("/stands/1/")
        self.assertEqual(len(response.context["history"]), 4)
        self.assertContains(response, "Иван Петров")
        self.assertContains(response, "Анна Смирнова")

    def test_number_of_queries(self):
        # Стенд, проверка занятости и история с арендаторами.
        with self.assertNumQueries(3):
            self.client.get("/stands/1/")

    def test_not_found_returns_404(self):
        response = self.client.get("/stands/999/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    def test_non_integer_id_is_not_routed(self):
        self.assertEqual(self.client.get("/stands/abc/").status_code, 404)

    def test_availability_on_booked_date(self):
        response = self.client.get("/stands/1/?date=2026-10-15")
        self.assertFalse(response.context["available"])
        self.assertContains(response, "занят")
        self.assertContains(response, "15.10.2026")

    def test_availability_on_free_date(self):
        response = self.client.get("/stands/1/?date=2026-10-16")
        self.assertTrue(response.context["available"])
        self.assertContains(response, "доступен")

    def test_cancelled_booking_does_not_block_date(self):
        response = self.client.get("/stands/1/?date=2026-10-20")
        self.assertTrue(response.context["available"])

    def test_invalid_date_falls_back_to_today(self):
        response = self.client.get("/stands/1/?date=oops")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверная дата")


class AvailableStandsViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def names(self, response):
        return [stand.name for stand in response.context["stands"]]

    def test_form_without_date_runs_no_search(self):
        response = self.client.get("/stands/available/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/available.html")
        self.assertContains(response, 'name="date"')
        self.assertEqual(len(self.names(response)), 0)
        self.assertNotContains(response, "свободных стендов нет")

    def test_busy_stands_are_excluded(self):
        response = self.client.get("/stands/available/?date=2026-10-15")
        self.assertEqual(
            self.names(response), ["Павильон Б", "Центральный остров"]
        )

    def test_cancelled_booking_does_not_make_stand_busy(self):
        response = self.client.get("/stands/available/?date=2026-10-20")
        self.assertEqual(len(self.names(response)), 4)

    def test_other_date(self):
        response = self.client.get("/stands/available/?date=2026-11-05")
        self.assertEqual(
            self.names(response), ["Павильон А", "Премиум-зона"]
        )

    def test_invalid_date(self):
        response = self.client.get("/stands/available/?date=32.13.2026")
        self.assertContains(response, "Неверная дата")
        self.assertEqual(len(self.names(response)), 0)

    def test_no_free_stands(self):
        from bookings.models import Booking

        Booking.objects.filter(booking_date=date(2026, 10, 15)).delete()
        for stand_id in (1, 2, 3, 4):
            Booking.objects.create(
                stand_id=stand_id, user_id=1, booking_date=date(2027, 1, 1)
            )
        response = self.client.get("/stands/available/?date=2027-01-01")
        self.assertContains(
            response, "На выбранную дату свободных стендов нет."
        )
