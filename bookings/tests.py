from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking, BookingManager, BookingQuerySet


class BookingModelTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_str(self):
        booking = Booking.objects.get(pk=2)
        self.assertEqual(
            str(booking), "Премиум-зона — 2026-10-15 (ООО «Сладкий мир»)"
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

    def test_old_boolean_field_is_removed(self):
        names = [field.name for field in Booking._meta.get_fields()]
        self.assertNotIn("is_cancelled", names)
        self.assertIn("status", names)

    def test_new_booking_is_active_by_default(self):
        booking = Booking.objects.create(
            stand_id=4, user_id=1, booking_date=date(2027, 5, 1)
        )
        self.assertEqual(booking.status, Booking.Status.ACTIVE)

    def test_status_choices_and_labels(self):
        self.assertEqual(
            Booking.Status.choices,
            [
                ("active", "Активно"),
                ("cancelled", "Отменено"),
                ("completed", "Завершено"),
            ],
        )
        self.assertEqual(
            Booking.objects.get(pk=3).get_status_display(), "Отменено"
        )

    def test_status_is_validated(self):
        booking = Booking.objects.get(pk=2)
        booking.status = "unknown"
        with self.assertRaises(ValidationError) as ctx:
            booking.full_clean()
        self.assertIn("status", ctx.exception.message_dict)

    def test_cancel_saves_to_database(self):
        booking = Booking.objects.get(pk=2)
        self.assertTrue(booking.is_active())
        booking.cancel()
        self.assertEqual(
            Booking.objects.get(pk=2).status, Booking.Status.CANCELLED
        )
        self.assertFalse(booking.is_active())

    def test_complete_saves_to_database(self):
        Booking.objects.get(pk=2).complete()
        self.assertEqual(
            Booking.objects.get(pk=2).status, Booking.Status.COMPLETED
        )

    def test_change_without_save_is_not_stored(self):
        booking = Booking.objects.get(pk=2)
        booking.status = Booking.Status.CANCELLED
        self.assertEqual(
            Booking.objects.get(pk=2).status, Booking.Status.ACTIVE
        )

    def test_one_active_booking_per_stand_and_date(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(
                stand_id=3, user_id=1, booking_date=date(2026, 10, 15)
            )

    def test_duplicate_active_booking_fails_validation_with_message(self):
        booking = Booking(
            stand_id=3, user_id=1, booking_date=date(2026, 10, 15)
        )
        with self.assertRaises(ValidationError) as ctx:
            booking.full_clean()
        self.assertIn(
            "уже есть активное бронирование", str(ctx.exception.messages)
        )

    def test_cancelled_and_completed_duplicates_are_allowed(self):
        for status in (Booking.Status.CANCELLED, Booking.Status.COMPLETED):
            Booking.objects.create(
                stand_id=3,
                user_id=1,
                booking_date=date(2026, 10, 15),
                status=status,
            )

    def test_delete_booking(self):
        Booking.objects.get(pk=9).delete()
        self.assertEqual(Booking.objects.count(), 8)


class BookingManagerTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_manager_is_built_on_custom_queryset(self):
        self.assertIsInstance(Booking.objects, BookingManager)
        self.assertIsInstance(Booking.objects.all(), BookingQuerySet)

    def test_status_methods(self):
        self.assertEqual(Booking.objects.active().count(), 7)
        self.assertEqual(Booking.objects.cancelled().count(), 1)
        self.assertEqual(Booking.objects.completed().count(), 1)
        self.assertEqual(
            [b.pk for b in Booking.objects.cancelled()], [3]
        )
        self.assertEqual(
            [b.pk for b in Booking.objects.completed()], [1]
        )

    def test_all_keeps_history(self):
        # all() возвращает все записи: активными по умолчанию они не стали.
        self.assertEqual(Booking.objects.all().count(), 9)
        self.assertEqual(
            Booking.objects.active().count()
            + Booking.objects.cancelled().count()
            + Booking.objects.completed().count(),
            Booking.objects.count(),
        )

    def test_for_date(self):
        pks = [b.pk for b in Booking.objects.for_date(date(2026, 10, 15))]
        self.assertEqual(pks, [1, 2])

    def test_methods_can_be_chained(self):
        pks = [
            b.pk
            for b in Booking.objects.active().for_date(date(2026, 10, 15))
        ]
        self.assertEqual(pks, [2])
        self.assertEqual(
            Booking.objects.active().filter(stand_id=1).count(), 2
        )

    def test_methods_return_querysets_evaluated_lazily(self):
        queryset = Booking.objects.active().for_date(date(2026, 10, 15))
        with self.assertNumQueries(0):
            repr(type(queryset))
        with self.assertNumQueries(1):
            list(queryset)


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
        # 7 активных броней, на странице первые 5, отсортированные по дате.
        self.assertEqual(self.ids(response), [2, 4, 5, 6, 7])
        self.assertEqual(response.context["total"], 7)
        self.assertContains(response, "Найдено бронирований: 7")
        self.assertNotContains(response, "booking-status-cancelled")
        self.assertNotContains(response, "booking-status-completed")

    def test_rows_are_dictionaries_with_related_values(self):
        first = self.client.get("/bookings/").context["bookings"][0]
        self.assertEqual(first["stand_name"], "Премиум-зона")
        self.assertEqual(first["user_name"], "ООО «Сладкий мир»")
        self.assertEqual(first["booking_date"], date(2026, 10, 15))
        self.assertEqual(first["status"], "active")

    def test_number_of_queries(self):
        # Контекстный процессор, количество, страница, стенды, арендаторы.
        with self.assertNumQueries(5):
            self.client.get("/bookings/")

    def test_filter_by_status(self):
        cancelled = self.client.get("/bookings/?status=cancelled")
        self.assertEqual(self.ids(cancelled), [3])
        self.assertContains(cancelled, "booking-status-cancelled")
        completed = self.client.get("/bookings/?status=completed")
        self.assertEqual(self.ids(completed), [1])
        self.assertContains(completed, "booking-status-completed")

    def test_status_all_shows_every_booking(self):
        response = self.client.get("/bookings/?status=all")
        self.assertEqual(response.context["total"], 9)
        for css in ("active", "cancelled", "completed"):
            self.assertContains(response, f"booking-status-{css}")

    def test_unknown_status_falls_back_to_active(self):
        response = self.client.get("/bookings/?status=hack")
        self.assertEqual(response.context["selected_status"], "active")
        self.assertEqual(response.context["total"], 7)

    def test_filter_by_date(self):
        response = self.client.get("/bookings/?date=2026-10-15")
        self.assertEqual(self.ids(response), [2])
        response = self.client.get("/bookings/?date=2026-10-15&status=all")
        self.assertEqual(self.ids(response), [1, 2])

    def test_filter_by_stand(self):
        response = self.client.get("/bookings/?stand=1")
        self.assertEqual(self.ids(response), [4, 9])

    def test_filter_by_user(self):
        response = self.client.get("/bookings/?user=3")
        self.assertEqual(self.ids(response), [5, 8])

    def test_filter_by_related_field_stand_type(self):
        response = self.client.get("/bookings/?type=Остров")
        self.assertEqual(self.ids(response), [7])

    def test_unknown_type_is_ignored(self):
        response = self.client.get("/bookings/?type=Неизвестный")
        self.assertEqual(response.context["total"], 7)

    def test_several_filters_combine_with_and(self):
        response = self.client.get("/bookings/?stand=1&user=2")
        self.assertEqual(self.ids(response), [4])
        response = self.client.get("/bookings/?stand=1&user=2&date=2026-10-15")
        self.assertEqual(self.ids(response), [])

    def test_filter_with_all_statuses(self):
        response = self.client.get("/bookings/?stand=1&status=all")
        self.assertEqual(self.ids(response), [1, 3, 4, 9])

    def test_search_in_related_fields(self):
        by_user = self.client.get("/bookings/?q=сладкий")
        self.assertEqual(self.ids(by_user), [2, 4, 7])
        by_stand = self.client.get("/bookings/?q=павильон б")
        self.assertEqual(self.ids(by_stand), [6, 8])
        by_email = self.client.get("/bookings/?q=ivan.petrov")
        self.assertEqual(self.ids(by_email), [6, 9])

    def test_invalid_filter_values_do_not_break_page(self):
        response = self.client.get("/bookings/?stand=abc&user=--&date=oops")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Укажите корректную дату.")
        self.assertEqual(response.context["total"], 7)

    def test_empty_result(self):
        response = self.client.get("/bookings/?q=несуществующий")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Бронирования не найдены.")

    def test_sort_by_stand_name(self):
        response = self.client.get("/bookings/?sort=stand")
        self.assertEqual(self.ids(response), [4, 9, 6, 8, 2])

    def test_sort_by_user_name(self):
        response = self.client.get("/bookings/?sort=user")
        self.assertEqual(self.ids(response), [5, 8, 6, 9, 2])

    def test_unknown_sort_falls_back_to_date(self):
        response = self.client.get("/bookings/?sort=pk;DROP")
        self.assertEqual(response.context["sort"], "date")
        self.assertEqual(self.ids(response), [2, 4, 5, 6, 7])

    def test_pagination_second_page(self):
        response = self.client.get("/bookings/?page=2")
        self.assertEqual(self.ids(response), [8, 9])
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_invalid_page_number_opens_first_page(self):
        response = self.client.get("/bookings/?page=abc")
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_too_large_page_number_opens_last_page(self):
        response = self.client.get("/bookings/?page=99")
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_pagination_links_keep_filters_and_sort(self):
        response = self.client.get("/bookings/?sort=stand&status=all")
        links = [
            line for line in response.content.decode().splitlines()
            if 'href="?' in line
        ]
        self.assertTrue(links)
        for link in links:
            self.assertIn("sort=stand", link)
            self.assertIn("status=all", link)

    def test_pagination_hidden_for_short_list(self):
        response = self.client.get("/bookings/?stand=3")
        self.assertNotContains(response, "pagination")

    def test_status_change_is_reflected_in_list(self):
        Booking.objects.get(pk=2).cancel()
        response = self.client.get("/bookings/")
        self.assertNotIn(2, self.ids(response))
        response = self.client.get("/bookings/?status=cancelled")
        self.assertEqual(self.ids(response), [2, 3])


class BookingDetailViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_detail_shows_related_objects(self):
        response = self.client.get("/bookings/2/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_detail.html")
        self.assertContains(response, "Бронирование №2")
        self.assertContains(response, "Премиум-зона")
        self.assertContains(response, "sweet@example.com")
        self.assertContains(response, "15.10.2026")
        self.assertContains(response, "booking-status-active")
        self.assertContains(response, 'href="/stands/premium-zona-3/"')

    def test_select_related_loads_in_one_query(self):
        # Контекстный процессор и бронирование со стендом и арендатором.
        with self.assertNumQueries(2):
            self.client.get("/bookings/2/")

    def test_statuses_on_detail_page(self):
        self.assertContains(self.client.get("/bookings/3/"), "Отменено")
        self.assertContains(self.client.get("/bookings/1/"), "Завершено")

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

    def test_totals_by_status(self):
        totals = self.get().context["totals"]
        self.assertEqual(totals["total_bookings"], 9)
        self.assertEqual(totals["active_bookings"], 7)
        self.assertEqual(totals["cancelled_bookings"], 1)
        self.assertEqual(totals["completed_bookings"], 1)

    def test_totals_by_area(self):
        totals = self.get().context["totals"]
        self.assertEqual(totals["stands_count"], 4)
        self.assertEqual(totals["min_area"], 18.5)
        self.assertEqual(totals["max_area"], 50.0)
        self.assertEqual(totals["total_area"], 129.5)
        self.assertAlmostEqual(totals["avg_area"], 32.375)

    def test_group_by_status(self):
        by_status = self.get().context["by_status"]
        self.assertEqual(
            [(row["label"], row["count"]) for row in by_status],
            [("Активно", 7), ("Отменено", 1), ("Завершено", 1)],
        )

    def test_statuses_change_after_status_update(self):
        Booking.objects.get(pk=2).cancel()
        totals = self.get().context["totals"]
        self.assertEqual(totals["active_bookings"], 6)
        self.assertEqual(totals["cancelled_bookings"], 2)
        self.assertEqual(totals["total_bookings"], 9)

    def test_counts_by_stand_count_only_active(self):
        by_stand = self.get().context["by_stand"]
        counts = {stand.name: stand.bookings_count for stand in by_stand}
        self.assertEqual(
            counts,
            {
                "Павильон А": 2,
                "Павильон Б": 2,
                "Премиум-зона": 2,
                "Центральный остров": 1,
            },
        )

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
                "Иван Петров": 2,
                "ООО «Сладкий мир»": 3,
                "Анна Смирнова": 2,
            },
        )
        self.assertEqual(by_user[0].name, "ООО «Сладкий мир»")

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
        # Контекстный процессор и семь запросов страницы.
        with self.assertNumQueries(9):
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
