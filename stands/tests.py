from django.test import SimpleTestCase

from tradestands.testing import TempDatabaseMixin


class StandListTests(TempDatabaseMixin, SimpleTestCase):
    def test_stand_list(self):
        response = self.client.get("/stands/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/stand_list.html")
        self.assertTemplateUsed(response, "stands/includes/stand_card.html")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, 'href="/stands/1/"')
        self.assertContains(response, "Найдено стендов: 4")

    def test_rows_are_accessible_by_name(self):
        response = self.client.get("/stands/")
        first = response.context["stands"][0]
        self.assertEqual(first["name"], "Павильон А")
        self.assertEqual(first["stand_type"], "Стандарт")

    def test_search_by_name_ignores_cyrillic_case(self):
        response = self.client.get("/stands/?q=павильон")
        names = [row["name"] for row in response.context["stands"]]
        self.assertEqual(names, ["Павильон А", "Павильон Б"])

    def test_filter_by_min_area(self):
        response = self.client.get("/stands/?min_area=30")
        names = [row["name"] for row in response.context["stands"]]
        self.assertEqual(names, ["Премиум-зона", "Центральный остров"])

    def test_filter_accepts_comma(self):
        response = self.client.get("/stands/?min_area=36,0")
        self.assertEqual(len(response.context["stands"]), 2)

    def test_search_and_filter_combined(self):
        response = self.client.get("/stands/?q=павильон&min_area=20")
        names = [row["name"] for row in response.context["stands"]]
        self.assertEqual(names, ["Павильон А"])

    def test_invalid_min_area_shows_warning(self):
        response = self.client.get("/stands/?min_area=abc")
        self.assertContains(response, "должна быть числом")
        self.assertEqual(len(response.context["stands"]), 4)

    def test_empty_result(self):
        response = self.client.get("/stands/?q=несуществующий")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Стенды не найдены.")

    def test_sql_injection_is_not_executed(self):
        payload = "'; DROP TABLE stands; --"
        response = self.client.get("/stands/", {"q": payload})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["stands"]), 0)
        # Таблица на месте, данные не изменились.
        response = self.client.get("/stands/")
        self.assertEqual(len(response.context["stands"]), 4)


class StandDetailTests(TempDatabaseMixin, SimpleTestCase):
    def test_stand_detail(self):
        response = self.client.get("/stands/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/stand_detail.html")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Площадь")

    def test_history_is_taken_from_join(self):
        response = self.client.get("/stands/1/")
        self.assertContains(response, "История бронирований")
        self.assertEqual(len(response.context["history"]), 3)
        self.assertContains(response, "Иван Петров")
        self.assertContains(response, "Анна Смирнова")

    def test_stand_detail_not_found(self):
        response = self.client.get("/stands/999/")
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.context["stand"])
        self.assertContains(response, "Стенд не найден", status_code=404)

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


class AvailableStandsTests(TempDatabaseMixin, SimpleTestCase):
    def test_form_without_date_runs_no_search(self):
        response = self.client.get("/stands/available/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/available.html")
        self.assertContains(response, 'name="date"')
        self.assertEqual(len(response.context["stands"]), 0)
        self.assertNotContains(response, "свободных стендов нет")

    def test_busy_stands_are_excluded(self):
        response = self.client.get("/stands/available/?date=2026-10-15")
        names = [row["name"] for row in response.context["stands"]]
        self.assertEqual(names, ["Павильон Б", "Центральный остров"])
        self.assertContains(response, "15.10.2026")

    def test_cancelled_booking_does_not_make_stand_busy(self):
        response = self.client.get("/stands/available/?date=2026-10-20")
        self.assertEqual(len(response.context["stands"]), 4)

    def test_date_without_bookings(self):
        response = self.client.get("/stands/available/?date=2030-01-01")
        self.assertEqual(len(response.context["stands"]), 4)

    def test_invalid_date(self):
        response = self.client.get("/stands/available/?date=32.13.2026")
        self.assertContains(response, "Неверная дата")
        self.assertEqual(len(response.context["stands"]), 0)

    def test_sql_injection_in_date_is_rejected(self):
        response = self.client.get(
            "/stands/available/", {"date": "2026-10-15' OR '1'='1"}
        )
        self.assertContains(response, "Неверная дата")

    def test_route_is_not_taken_for_int_converter(self):
        response = self.client.get("/stands/available/")
        self.assertEqual(response.status_code, 200)
