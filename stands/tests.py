from unittest.mock import patch

from django.test import SimpleTestCase


class StandsViewsTests(SimpleTestCase):
    def test_stand_list(self):
        response = self.client.get("/stands/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Павильон А")
        self.assertContains(response, 'href="/stands/1/"')

    def test_stand_list_templates_and_context(self):
        response = self.client.get("/stands/")
        self.assertTemplateUsed(response, "stands/stand_list.html")
        self.assertTemplateUsed(response, "stands/includes/stand_card.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertEqual(len(response.context["stands"]), 4)
        self.assertContains(response, "Всего стендов: 4")

    def test_stand_list_empty(self):
        with patch("stands.views.load_dataset", return_value=([], [], [])):
            response = self.client.get("/stands/")
        self.assertContains(response, "Стенды не найдены.")
        self.assertContains(response, "Всего стендов: 0")

    def test_stand_detail(self):
        response = self.client.get("/stands/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "stands/stand_detail.html")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Площадь")

    def test_stand_detail_not_found(self):
        response = self.client.get("/stands/999/")
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.context["stand"])
        self.assertContains(
            response, "Стенд не найден", status_code=404
        )

    def test_non_integer_id_is_not_routed(self):
        self.assertEqual(self.client.get("/stands/abc/").status_code, 404)

    def test_availability_on_booked_date(self):
        response = self.client.get("/stands/1/?date=2026-10-15")
        self.assertContains(response, "занят")
        self.assertContains(response, "15.10.2026")

    def test_availability_on_free_date(self):
        response = self.client.get("/stands/1/?date=2026-10-16")
        self.assertContains(response, "доступен")

    def test_cancelled_booking_does_not_block_date(self):
        response = self.client.get("/stands/1/?date=2026-10-20")
        self.assertContains(response, "доступен")

    def test_invalid_date_falls_back_to_today(self):
        response = self.client.get("/stands/1/?date=oops")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверная дата")
