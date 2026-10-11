from django.test import SimpleTestCase


class BookingsViewsTests(SimpleTestCase):
    def test_booking_list(self):
        response = self.client.get("/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Павильон А")
        self.assertContains(response, 'href="/bookings/1/"')
        self.assertContains(response, "отменено")

    def test_booking_detail_shows_related_objects(self):
        response = self.client.get("/bookings/1/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Бронирование №1")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Иван Петров")

    def test_booking_detail_not_found(self):
        response = self.client.get("/bookings/999/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response, "Бронирование не найдено", status_code=404
        )
