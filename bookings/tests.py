from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking


class BookingModelTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_str(self):
        booking = Booking.objects.get(pk=1)
        self.assertEqual(
            str(booking), "Павильон А — 2026-10-15 (Иван Петров)"
        )

    def test_default_ordering_by_date_then_pk(self):
        pks = list(Booking.objects.values_list("pk", flat=True))
        self.assertEqual(pks, [1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_forward_relations(self):
        booking = Booking.objects.select_related("stand", "user").get(pk=2)
        self.assertEqual(booking.stand.name, "Премиум-зона")
        self.assertEqual(booking.user.name, "ООО «Сладкий мир»")

    def test_fk_attribute_and_object(self):
        booking = Booking.objects.get(pk=1)
        self.assertEqual(booking.stand_id, 1)
        self.assertEqual(booking.stand.pk, 1)

    def test_booking_date_is_a_date(self):
        booking = Booking.objects.get(pk=1)
        self.assertEqual(booking.booking_date, date(2026, 10, 15))

    def test_cancel_saves_to_database(self):
        booking = Booking.objects.get(pk=1)
        self.assertTrue(booking.is_active())
        booking.cancel()
        self.assertTrue(Booking.objects.get(pk=1).is_cancelled)
        self.assertFalse(booking.is_active())

    def test_change_without_save_is_not_stored(self):
        booking = Booking.objects.get(pk=1)
        booking.is_cancelled = True
        self.assertFalse(Booking.objects.get(pk=1).is_cancelled)

    def test_one_active_booking_per_stand_and_date(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(
                stand_id=1, user_id=2, booking_date=date(2026, 10, 15)
            )

    def test_cancelled_duplicate_is_allowed(self):
        Booking.objects.create(
            stand_id=1,
            user_id=2,
            booking_date=date(2026, 10, 15),
            is_cancelled=True,
        )

    def test_new_booking_is_active_by_default(self):
        booking = Booking.objects.create(
            stand_id=4, user_id=1, booking_date=date(2027, 5, 1)
        )
        self.assertFalse(booking.is_cancelled)

    def test_delete_booking(self):
        Booking.objects.get(pk=9).delete()
        self.assertEqual(Booking.objects.count(), 8)


class BookingListViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def ids(self, response):
        return [row["id"] for row in response.context["bookings"]]

    def test_default_list_has_only_active_bookings(self):
        response = self.client.get("/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_list.html")
        self.assertTemplateUsed(
            response, "bookings/includes/booking_status.html"
        )
        # 8 активных броней, на странице первые 5, отсортированные по дате.
        self.assertEqual(self.ids(response), [1, 2, 4, 5, 6])
        self.assertEqual(response.context["total"], 8)
        self.assertContains(response, "Найдено активных бронирований: 8")
        self.assertNotContains(response, "booking-status-cancelled")

    def test_rows_are_dictionaries_with_related_values(self):
        first = self.client.get("/bookings/").context["bookings"][0]
        self.assertEqual(first["stand_name"], "Павильон А")
        self.assertEqual(first["user_name"], "Иван Петров")
        self.assertEqual(first["booking_date"], date(2026, 10, 15))

    def test_number_of_queries(self):
        # Количество, страница, список стендов, список арендаторов.
        with self.assertNumQueries(4):
            self.client.get("/bookings/")

    def test_show_all_includes_cancelled(self):
        response = self.client.get("/bookings/?show=all")
        self.assertEqual(response.context["total"], 9)
        self.assertContains(response, "booking-status-cancelled")

    def test_filter_by_date(self):
        response = self.client.get("/bookings/?date=2026-10-15")
        self.assertEqual(self.ids(response), [1, 2])

    def test_filter_by_stand(self):
        response = self.client.get("/bookings/?stand=1")
        self.assertEqual(self.ids(response), [1, 4, 9])

    def test_filter_by_user(self):
        response = self.client.get("/bookings/?user=3")
        self.assertEqual(self.ids(response), [5, 8])

    def test_filter_by_related_field_stand_type(self):
        response = self.client.get("/bookings/?type=Остров")
        self.assertEqual(self.ids(response), [7])

    def test_unknown_type_is_ignored(self):
        response = self.client.get("/bookings/?type=Неизвестный")
        self.assertEqual(response.context["total"], 8)

    def test_several_filters_combine_with_and(self):
        response = self.client.get("/bookings/?stand=1&user=2")
        self.assertEqual(self.ids(response), [4])
        response = self.client.get("/bookings/?stand=1&user=2&date=2026-10-15")
        self.assertEqual(self.ids(response), [])

    def test_filter_with_cancelled(self):
        response = self.client.get("/bookings/?stand=1&show=all")
        self.assertEqual(self.ids(response), [1, 3, 4, 9])

    def test_search_in_related_fields(self):
        by_user = self.client.get("/bookings/?q=сладкий")
        self.assertEqual(self.ids(by_user), [2, 4, 7])
        by_stand = self.client.get("/bookings/?q=павильон б")
        self.assertEqual(self.ids(by_stand), [6, 8])
        by_email = self.client.get("/bookings/?q=ivan.petrov")
        self.assertEqual(self.ids(by_email), [1, 6, 9])

    def test_invalid_filter_values_do_not_break_page(self):
        response = self.client.get("/bookings/?stand=abc&user=--&date=oops")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Укажите корректную дату.")
        self.assertEqual(response.context["total"], 8)

    def test_empty_result(self):
        response = self.client.get("/bookings/?q=несуществующий")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Бронирования не найдены.")

    def test_sort_by_stand_name(self):
        response = self.client.get("/bookings/?sort=stand")
        self.assertEqual(self.ids(response), [1, 4, 9, 6, 8])

    def test_sort_by_user_name(self):
        response = self.client.get("/bookings/?sort=user")
        self.assertEqual(self.ids(response), [5, 8, 1, 6, 9])

    def test_unknown_sort_falls_back_to_date(self):
        response = self.client.get("/bookings/?sort=pk;DROP")
        self.assertEqual(response.context["sort"], "date")
        self.assertEqual(self.ids(response), [1, 2, 4, 5, 6])

    def test_pagination_second_page(self):
        response = self.client.get("/bookings/?page=2")
        self.assertEqual(self.ids(response), [7, 8, 9])
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_invalid_page_number_opens_first_page(self):
        response = self.client.get("/bookings/?page=abc")
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_too_large_page_number_opens_last_page(self):
        response = self.client.get("/bookings/?page=99")
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_pagination_links_keep_filters_and_sort(self):
        response = self.client.get("/bookings/?sort=stand&show=all")
        self.assertContains(response, "sort=stand")
        links = [
            line for line in response.content.decode().splitlines()
            if 'href="?' in line
        ]
        self.assertTrue(links)
        for link in links:
            self.assertIn("sort=stand", link)
            self.assertIn("show=all", link)

    def test_pagination_hidden_for_short_list(self):
        response = self.client.get("/bookings/?stand=3")
        self.assertNotContains(response, "pagination")


class BookingDetailViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_detail_shows_related_objects(self):
        response = self.client.get("/bookings/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_detail.html")
        self.assertContains(response, "Бронирование №1")
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Иван Петров")
        self.assertContains(response, "ivan.petrov@example.com")
        self.assertContains(response, "15.10.2026")
        self.assertContains(response, "booking-status-active")

    def test_select_related_loads_in_one_query(self):
        with self.assertNumQueries(1):
            self.client.get("/bookings/1/")

    def test_cancelled_booking_detail(self):
        response = self.client.get("/bookings/3/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Отменено")

    def test_not_found_returns_404(self):
        response = self.client.get("/bookings/999999/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")


class StatisticsViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def get(self):
        return self.client.get("/bookings/statistics/")

    def test_page(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/statistics.html")
        self.assertContains(response, "Статистика бронирований")

    def test_totals(self):
        totals = self.get().context["totals"]
        self.assertEqual(totals["active_bookings"], 8)
        self.assertEqual(totals["stands_count"], 4)
        self.assertEqual(totals["min_area"], 18.5)
        self.assertEqual(totals["max_area"], 50.0)
        self.assertEqual(totals["total_area"], 129.5)
        self.assertAlmostEqual(totals["avg_area"], 32.375)

    def test_counts_by_stand_exclude_cancelled(self):
        by_stand = self.get().context["by_stand"]
        counts = {stand.name: stand.bookings_count for stand in by_stand}
        self.assertEqual(
            counts,
            {
                "Павильон А": 3,
                "Павильон Б": 2,
                "Премиум-зона": 2,
                "Центральный остров": 1,
            },
        )
        self.assertEqual(by_stand[0].name, "Павильон А")

    def test_stand_without_active_bookings_stays_in_statistics(self):
        Booking.objects.filter(stand_id=4).delete()
        by_stand = self.get().context["by_stand"]
        counts = {stand.name: stand.bookings_count for stand in by_stand}
        self.assertEqual(counts["Центральный остров"], 0)
        self.assertEqual(len(counts), 4)

    def test_counts_by_user(self):
        by_user = self.get().context["by_user"]
        counts = {user.name: user.bookings_count for user in by_user}
        self.assertEqual(
            counts,
            {
                "Иван Петров": 3,
                "ООО «Сладкий мир»": 3,
                "Анна Смирнова": 2,
            },
        )

    def test_group_by_stand_type(self):
        by_type = list(self.get().context["by_type"])
        self.assertEqual(
            [row["stand_type"] for row in by_type],
            ["Остров", "Премиум", "Стандарт"],
        )
        standard = by_type[2]
        self.assertEqual(standard["stands_count"], 2)
        self.assertAlmostEqual(standard["avg_area"], 21.75)

    def test_popular_stands_filter_by_aggregate(self):
        popular = self.get().context["popular"]
        names = [stand.name for stand in popular]
        self.assertEqual(
            names, ["Павильон А", "Павильон Б", "Премиум-зона"]
        )

    def test_latest_bookings_slice(self):
        latest = self.get().context["latest"]
        self.assertEqual([b.pk for b in latest], [9, 8, 7])

    def test_number_of_queries(self):
        with self.assertNumQueries(7):
            self.get()


class NavigationTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_named_urls(self):
        self.assertEqual(reverse("bookings:bookings"), "/bookings/")
        self.assertEqual(reverse("bookings:detail", args=[1]), "/bookings/1/")
        self.assertEqual(
            reverse("bookings:statistics"), "/bookings/statistics/"
        )
        self.assertEqual(reverse("stands:available"), "/stands/available/")

    def test_links_in_navigation(self):
        response = self.client.get("/")
        self.assertContains(response, 'href="/bookings/statistics/"')
        response = self.client.get("/stands/")
        self.assertContains(response, 'href="/stands/available/"')
