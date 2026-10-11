from unittest.mock import patch

from django.test import SimpleTestCase


class BookingsViewsTests(SimpleTestCase):
    def test_booking_list(self):
        response = self.client.get("/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Павильон А")
        self.assertContains(response, 'href="/bookings/1/"')

    def test_booking_list_templates_and_context(self):
        response = self.client.get("/bookings/")
        self.assertTemplateUsed(response, "bookings/booking_list.html")
        self.assertTemplateUsed(
            response, "bookings/includes/booking_status.html"
        )
        self.assertEqual(len(response.context["bookings"]), 3)
        self.assertContains(response, "Всего бронирований: 3")

    def test_booking_list_shows_both_statuses(self):
        response = self.client.get("/bookings/")
        self.assertContains(response, "booking-status-active")
        self.assertContains(response, "booking-status-cancelled")

    def test_booking_list_empty(self):
        with patch(
            "bookings.views.load_dataset", return_value=([], [], [])
        ):
            response = self.client.get("/bookings/")
        self.assertContains(response, "Бронирования не найдены.")

    def test_booking_detail_shows_related_objects(self):
        response = self.client.get("/bookings/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_detail.html")
        self.assertContains(response, "Бронирование №1")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Иван Петров")
        self.assertContains(response, "booking-status-active")

    def test_cancelled_booking_detail(self):
        response = self.client.get("/bookings/3/")
        self.assertContains(response, "Отменено")

    def test_booking_detail_not_found(self):
        response = self.client.get("/bookings/999/")
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.context["booking"])
        self.assertContains(
            response, "Бронирование не найдено", status_code=404
        )
