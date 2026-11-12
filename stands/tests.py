from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking
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

    def test_reverse_relation_and_manager_methods(self):
        stand = Stand.objects.get(pk=1)
        self.assertEqual(stand.bookings.count(), 4)
        self.assertEqual(stand.bookings.active().count(), 2)
        self.assertEqual(stand.bookings.completed().count(), 1)
        self.assertEqual(stand.bookings.cancelled().count(), 1)

    def test_is_available_on_considers_only_active_bookings(self):
        stand = Stand.objects.get(pk=1)
        # Активное бронирование блокирует стенд.
        self.assertFalse(stand.is_available_on(date(2026, 10, 22)))
        # Завершённое и отменённое бронирования стенд не блокируют.
        self.assertTrue(stand.is_available_on(date(2026, 10, 15)))
        self.assertTrue(stand.is_available_on(date(2026, 10, 20)))
        self.assertTrue(stand.is_available_on(date(2030, 1, 1)))


class StandSlugTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_existing_slugs_are_transliterated_and_unique(self):
        slugs = list(Stand.objects.values_list("slug", flat=True))
        self.assertEqual(
            sorted(slugs),
            [
                "pavilon-a-1",
                "pavilon-b-2",
                "premium-zona-3",
                "tsentralnyi-ostrov-4",
            ],
        )

    def test_new_stand_gets_slug_with_primary_key(self):
        stand = Stand.objects.create(name="Аудитория 301", area=30)
        self.assertEqual(stand.slug, f"auditoriia-301-{stand.pk}")
        stand.refresh_from_db()
        self.assertTrue(stand.slug.endswith(f"-{stand.pk}"))

    def test_slug_is_not_changed_by_renaming(self):
        stand = Stand.objects.get(pk=1)
        stand.name = "Совсем другое название"
        stand.save()
        stand.refresh_from_db()
        self.assertEqual(stand.slug, "pavilon-a-1")

    def test_name_without_latin_symbols_still_gets_slug(self):
        stand = Stand.objects.create(name="!!!", area=10)
        self.assertEqual(stand.slug, f"stand-{stand.pk}")

    def test_slug_is_unique_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Stand.objects.filter(pk=2).update(slug="pavilon-a-1")

    def test_get_absolute_url(self):
        stand = Stand.objects.get(pk=1)
        self.assertEqual(stand.get_absolute_url(), "/stands/pavilon-a-1/")
        self.assertEqual(
            stand.get_absolute_url(),
            reverse("stands:detail", kwargs={"slug": "pavilon-a-1"}),
        )


class StandGeneratedFieldTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_is_large_is_computed_by_database(self):
        flags = dict(Stand.objects.values_list("name", "is_large"))
        self.assertEqual(
            flags,
            {
                "Павильон А": False,
                "Павильон Б": False,
                "Премиум-зона": True,
                "Центральный остров": False,
            },
        )

    def test_is_large_is_recalculated_after_area_change(self):
        stand = Stand.objects.get(pk=1)
        stand.area = 45
        stand.save()
        stand.refresh_from_db()
        self.assertTrue(stand.is_large)

        stand.area = 20
        stand.save()
        stand.refresh_from_db()
        self.assertFalse(stand.is_large)

    def test_boundary_value(self):
        stand = Stand.objects.create(name="Граница", area=40)
        stand.refresh_from_db()
        self.assertTrue(stand.is_large)

    def test_generated_field_is_not_editable(self):
        self.assertFalse(Stand._meta.get_field("is_large").editable)


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

    def test_links_use_get_absolute_url(self):
        response = self.client.get("/stands/")
        self.assertContains(response, 'href="/stands/pavilon-a-1/"')

    def test_large_stand_is_marked(self):
        response = self.client.get("/stands/")
        self.assertContains(response, "Большой", count=1)

    def test_context_contains_model_objects(self):
        stand = self.client.get("/stands/").context["stands"][0]
        self.assertIsInstance(stand, Stand)

    def test_search_by_name(self):
        response = self.client.get("/stands/?q=павильон")
        self.assertEqual(self.names(response), ["Павильон А", "Павильон Б"])

    def test_numeric_search_also_matches_area(self):
        response = self.client.get("/stands/?q=36")
        self.assertEqual(self.names(response), ["Центральный остров"])
        response = self.client.get("/stands/?q=18,5")
        self.assertEqual(self.names(response), ["Павильон Б"])

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

    def test_sort_by_area_descending(self):
        response = self.client.get("/stands/?sort=area&direction=desc")
        self.assertEqual(
            self.names(response),
            [
                "Премиум-зона",
                "Центральный остров",
                "Павильон А",
                "Павильон Б",
            ],
        )

    def test_sort_by_area_ascending(self):
        response = self.client.get("/stands/?sort=area")
        self.assertEqual(self.names(response)[0], "Павильон Б")

    def test_unknown_sort_and_direction_fall_back_to_defaults(self):
        response = self.client.get("/stands/?sort=pk;DROP&direction=up")
        self.assertEqual(response.context["sort"], "name")
        self.assertEqual(response.context["direction"], "asc")
        self.assertEqual(self.names(response)[0], "Павильон А")

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
    url = "/stands/pavilon-a-1/"

    def test_detail_by_slug(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/stand_detail.html")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Площадь")
        self.assertIsInstance(response.context["stand"], Stand)

    def test_large_stand_badge(self):
        response = self.client.get("/stands/premium-zona-3/")
        self.assertContains(response, "Большой стенд")
        response = self.client.get(self.url)
        self.assertNotContains(response, "Большой стенд")

    def test_history_through_reverse_relation_shows_all_statuses(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["history"]), 4)
        self.assertContains(response, "booking-status-active")
        self.assertContains(response, "booking-status-cancelled")
        self.assertContains(response, "booking-status-completed")
        self.assertContains(response, "Иван Петров")

    def test_number_of_queries(self):
        # Контекстный процессор, стенд, проверка занятости и история.
        with self.assertNumQueries(4):
            self.client.get(self.url)

    def test_unknown_slug_returns_404(self):
        response = self.client.get("/stands/net-takogo-99/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    def test_numeric_id_is_not_a_slug_of_existing_stand(self):
        self.assertEqual(self.client.get("/stands/1/").status_code, 404)

    def test_invalid_slug_is_not_routed(self):
        self.assertEqual(self.client.get("/stands/Не слаг/").status_code, 404)

    def test_availability_on_booked_date(self):
        response = self.client.get(self.url + "?date=2026-10-22")
        self.assertFalse(response.context["available"])
        self.assertContains(response, "занят")
        self.assertContains(response, "22.10.2026")

    def test_availability_on_free_date(self):
        response = self.client.get(self.url + "?date=2026-10-16")
        self.assertTrue(response.context["available"])
        self.assertContains(response, "доступен")

    def test_cancelled_and_completed_bookings_do_not_block_date(self):
        for day in ("2026-10-20", "2026-10-15"):
            response = self.client.get(self.url + f"?date={day}")
            self.assertTrue(response.context["available"], day)

    def test_invalid_date_falls_back_to_today(self):
        response = self.client.get(self.url + "?date=oops")
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
        response = self.client.get("/stands/available/?date=2026-10-22")
        self.assertEqual(
            self.names(response),
            ["Павильон Б", "Премиум-зона", "Центральный остров"],
        )

    def test_completed_booking_does_not_make_stand_busy(self):
        # На 2026-10-15 у стенда «Павильон А» только завершённая бронь.
        response = self.client.get("/stands/available/?date=2026-10-15")
        self.assertEqual(
            self.names(response),
            ["Павильон А", "Павильон Б", "Центральный остров"],
        )

    def test_cancelled_booking_does_not_make_stand_busy(self):
        response = self.client.get("/stands/available/?date=2026-10-20")
        self.assertEqual(len(self.names(response)), 4)

    def test_other_date(self):
        response = self.client.get("/stands/available/?date=2026-11-05")
        self.assertEqual(
            self.names(response), ["Павильон А", "Премиум-зона"]
        )

    def test_status_change_changes_availability(self):
        url = "/stands/available/?date=2026-10-22"
        self.assertNotIn("Павильон А", self.names(self.client.get(url)))
        Booking.objects.get(pk=4).cancel()
        self.assertIn("Павильон А", self.names(self.client.get(url)))

    def test_invalid_date(self):
        response = self.client.get("/stands/available/?date=32.13.2026")
        self.assertContains(response, "Неверная дата")
        self.assertEqual(len(self.names(response)), 0)

    def test_no_free_stands(self):
        for stand_id in (1, 2, 3, 4):
            Booking.objects.create(
                stand_id=stand_id, user_id=1, booking_date=date(2027, 1, 1)
            )
        response = self.client.get("/stands/available/?date=2027-01-01")
        self.assertContains(
            response, "На выбранную дату свободных стендов нет."
        )
