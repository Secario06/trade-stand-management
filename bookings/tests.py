from django.test import SimpleTestCase
from django.urls import reverse

from db.database import get_connection
from tradestands.testing import TempDatabaseMixin


class BookingListTests(TempDatabaseMixin, SimpleTestCase):
    def test_list_shows_only_active_bookings(self):
        response = self.client.get("/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_list.html")
        self.assertTemplateUsed(
            response, "bookings/includes/booking_status.html"
        )
        self.assertEqual(len(response.context["bookings"]), 4)
        self.assertContains(response, "Активных бронирований: 4")
        self.assertContains(response, 'href="/bookings/1/"')
        self.assertNotContains(response, "Бронирование №3")
        self.assertNotContains(response, "booking-status-cancelled")

    def test_list_joins_stand_and_user(self):
        response = self.client.get("/bookings/")
        first = response.context["bookings"][0]
        self.assertEqual(first["stand_name"], "Павильон А")
        self.assertEqual(first["user_name"], "Иван Петров")

    def test_show_all_adds_cancelled(self):
        response = self.client.get("/bookings/?show=all")
        self.assertEqual(len(response.context["bookings"]), 5)
        self.assertContains(response, "Все бронирования: 5")
        self.assertContains(response, "booking-status-cancelled")
        self.assertContains(response, "booking-status-active")

    def test_empty_list(self):
        conn = get_connection()
        conn.execute("DELETE FROM bookings")
        conn.commit()
        conn.close()
        response = self.client.get("/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Бронирования не найдены.")


class BookingDetailTests(TempDatabaseMixin, SimpleTestCase):
    def test_detail_shows_related_objects(self):
        response = self.client.get("/bookings/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_detail.html")
        self.assertContains(response, "Бронирование №1")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Иван Петров")
        self.assertContains(response, "ivan.petrov@example.com")
        self.assertContains(response, "booking-status-active")

    def test_cancelled_booking_detail(self):
        response = self.client.get("/bookings/3/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Отменено")

    def test_detail_not_found(self):
        response = self.client.get("/bookings/999/")
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(response.context["booking"])
        self.assertContains(
            response, "Бронирование не найдено", status_code=404
        )


class StatisticsTests(TempDatabaseMixin, SimpleTestCase):
    def test_statistics_page(self):
        response = self.client.get("/bookings/statistics/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/statistics.html")
        self.assertContains(response, "Статистика бронирований")

    def test_totals(self):
        totals = self.client.get("/bookings/statistics/").context["totals"]
        self.assertEqual(totals["active_bookings"], 4)
        self.assertEqual(totals["stands_count"], 4)
        self.assertEqual(totals["min_area"], 18.5)
        self.assertEqual(totals["max_area"], 50.0)
        self.assertEqual(totals["total_area"], 129.5)
        self.assertAlmostEqual(totals["avg_area"], 32.375)

    def test_group_by_includes_stands_without_bookings(self):
        by_stand = self.client.get("/bookings/statistics/").context["by_stand"]
        counts = {row["stand_name"]: row["bookings_count"] for row in by_stand}
        self.assertEqual(counts["Павильон А"], 2)
        self.assertEqual(counts["Премиум-зона"], 2)
        self.assertEqual(counts["Павильон Б"], 0)
        self.assertEqual(counts["Центральный остров"], 0)

    def test_group_by_user(self):
        by_user = self.client.get("/bookings/statistics/").context["by_user"]
        self.assertEqual(by_user[0]["user_name"], "ООО «Сладкий мир»")
        self.assertEqual(by_user[0]["bookings_count"], 2)

    def test_having_selects_popular_stands(self):
        popular = self.client.get("/bookings/statistics/").context["popular"]
        names = [row["stand_name"] for row in popular]
        self.assertEqual(names, ["Павильон А", "Премиум-зона"])

    def test_latest_bookings_limit(self):
        latest = self.client.get("/bookings/statistics/").context["latest"]
        self.assertEqual([row["id"] for row in latest], [5, 4, 3])


class NavigationTests(TempDatabaseMixin, SimpleTestCase):
    def test_statistics_link_in_navigation(self):
        self.assertEqual(
            reverse("bookings:statistics"), "/bookings/statistics/"
        )
        self.assertEqual(
            reverse("stands:available"), "/stands/available/"
        )
        response = self.client.get("/")
        self.assertContains(response, 'href="/bookings/statistics/"')
        response = self.client.get("/stands/")
        self.assertContains(response, 'href="/stands/available/"')
