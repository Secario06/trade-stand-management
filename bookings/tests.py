from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.forms import BookingFilterForm, BookingForm
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
        self.assertContains(
            response, "Проверьте введённые значения фильтров."
        )
        # Ошибка отображается у каждого некорректного поля.
        self.assertContains(response, "Введите правильную дату.")
        self.assertContains(response, "Выберите корректный вариант.")
        # Некорректные фильтры не применяются, показаны активные брони.
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


class BookingFilterFormTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_form_is_plain_form_not_model_form(self):
        self.assertFalse(hasattr(BookingFilterForm, "_meta"))
        self.assertTrue(hasattr(BookingForm, "_meta"))

    def test_empty_request_gives_unbound_form_without_errors(self):
        response = self.client.get("/bookings/")
        form = response.context["form"]
        self.assertFalse(form.is_bound)
        self.assertIsNone(response.context["error"])
        self.assertNotContains(response, 'class="form-error"')

    def test_valid_data_gives_cleaned_values(self):
        form = BookingFilterForm(
            {
                "date": "2026-10-15",
                "stand": "3",
                "user": "2",
                "type": "Премиум",
                "status": "all",
                "sort": "stand",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["date"], date(2026, 10, 15))
        self.assertEqual(form.cleaned_data["stand"].pk, 3)
        self.assertEqual(form.cleaned_data["user"].pk, 2)
        self.assertEqual(form.cleaned_data["sort"], "stand")

    def test_invalid_values_are_rejected(self):
        for field, value in (
            ("date", "не_дата"),
            ("stand", "999999"),
            ("user", "999999"),
            ("type", "Неизвестный"),
            ("status", "hack"),
            ("sort", "unknown"),
        ):
            form = BookingFilterForm({field: value})
            self.assertFalse(form.is_valid(), field)
            self.assertIn(field, form.errors)

    def test_invalid_form_shows_message_and_default_list(self):
        for query in (
            "date=не_дата",
            "stand=999999",
            "sort=unknown",
            "status=hack",
        ):
            response = self.client.get(f"/bookings/?{query}")
            self.assertEqual(response.status_code, 200, query)
            self.assertContains(
                response, "Проверьте введённые значения фильтров."
            )
            self.assertEqual(response.context["total"], 7, query)
            self.assertEqual(response.context["sort"], "date", query)

    def test_selected_values_are_kept_in_form(self):
        response = self.client.get(
            "/bookings/?stand=1&date=2026-10-22&sort=user&status=all"
        )
        self.assertContains(response, 'value="2026-10-22"')
        form = response.context["form"]
        self.assertEqual(form["stand"].value(), "1")
        self.assertEqual(form["sort"].value(), "user")


class BookingFormTests(TestCase):
    fixtures = ["tradestands.json"]

    def setUp(self):
        self.today = timezone.localdate()
        self.future = self.today + timedelta(days=30)

    def data(self, booking_date, stand=1, user=1):
        return {"stand": stand, "user": user, "booking_date": booking_date}

    def test_form_fields_exclude_status(self):
        self.assertEqual(
            list(BookingForm().fields), ["stand", "user", "booking_date"]
        )

    def test_labels_help_texts_and_widgets(self):
        form = BookingForm()
        self.assertEqual(form.fields["stand"].label, "Стенд")
        self.assertEqual(
            form.fields["booking_date"].label, "Дата бронирования"
        )
        self.assertTrue(form.fields["booking_date"].help_text)
        widget = form.fields["booking_date"].widget
        self.assertEqual(widget.input_type, "date")
        self.assertEqual(widget.attrs["class"], "form-control")

    def test_valid_data(self):
        form = BookingForm(self.data(self.future.isoformat()))
        self.assertTrue(form.is_valid(), form.errors)

    def test_past_date_is_rejected(self):
        yesterday = self.today - timedelta(days=1)
        form = BookingForm(self.data(yesterday.isoformat()))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["booking_date"],
            ["Нельзя создать бронирование на прошедшую дату."],
        )

    def test_today_is_allowed(self):
        form = BookingForm(self.data(self.today.isoformat()))
        self.assertTrue(form.is_valid(), form.errors)

    def test_required_fields(self):
        form = BookingForm({})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            set(form.errors), {"stand", "user", "booking_date"}
        )

    def test_unchanged_past_date_of_existing_booking_is_allowed(self):
        # Бронирование №2 находится в прошлом: смена арендатора допустима.
        booking = Booking.objects.get(pk=2)
        form = BookingForm(
            self.data(booking.booking_date.isoformat(), stand=3, user=1),
            instance=booking,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_changing_date_to_the_past_is_rejected_on_edit(self):
        booking = Booking.objects.get(pk=9)
        form = BookingForm(
            self.data("2020-01-01", stand=1, user=1), instance=booking
        )
        self.assertFalse(form.is_valid())
        self.assertIn("booking_date", form.errors)


class BookingCreateViewTests(TestCase):
    fixtures = ["tradestands.json"]
    url = "/bookings/create/"

    def setUp(self):
        self.today = timezone.localdate()
        self.future = self.today + timedelta(days=60)

    def post(self, booking_date, stand=4, user=1, **extra):
        return self.client.post(
            self.url,
            {"stand": stand, "user": user, "booking_date": booking_date},
            **extra,
        )

    def test_get_shows_empty_form_with_today(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_form.html")
        self.assertFalse(response.context["form"].is_bound)
        self.assertContains(response, "Создание бронирования")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, f'value="{self.today.isoformat()}"')
        self.assertContains(response, "Выберите стенд для бронирования.")

    def test_valid_post_creates_active_booking_and_redirects(self):
        before = Booking.objects.count()
        response = self.post(self.future.isoformat(), follow=True)
        self.assertRedirects(response, "/bookings/")
        self.assertEqual(Booking.objects.count(), before + 1)
        booking = Booking.objects.latest("pk")
        self.assertEqual(booking.stand_id, 4)
        self.assertEqual(booking.user_id, 1)
        self.assertEqual(booking.booking_date, self.future)
        self.assertEqual(booking.status, Booking.Status.ACTIVE)
        self.assertContains(response, f"Бронирование №{booking.pk} создано.")

    def test_new_booking_appears_in_list(self):
        self.post(self.future.isoformat())
        response = self.client.get(
            f"/bookings/?date={self.future.isoformat()}"
        )
        self.assertEqual(response.context["total"], 1)

    def test_past_date_shows_field_error_and_saves_nothing(self):
        before = Booking.objects.count()
        yesterday = (self.today - timedelta(days=1)).isoformat()
        response = self.post(yesterday)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Нельзя создать бронирование на прошедшую дату."
        )
        self.assertEqual(Booking.objects.count(), before)
        # Введённые значения сохраняются при повторном показе формы.
        self.assertContains(response, f'value="{yesterday}"')

    def test_today_is_allowed(self):
        response = self.post(self.today.isoformat())
        self.assertRedirects(response, "/bookings/")

    def test_missing_field_shows_error(self):
        response = self.client.post(self.url, {"stand": 4, "user": 1})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Обязательное поле.")

    def test_invalid_date_shows_error(self):
        response = self.post("не_дата")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите правильную дату.")

    def test_unknown_stand_is_rejected(self):
        before = Booking.objects.count()
        response = self.post(self.future.isoformat(), stand=999)
        self.assertContains(response, "Выберите корректный вариант.")
        self.assertEqual(Booking.objects.count(), before)

    def test_busy_stand_shows_non_field_error(self):
        Booking.objects.create(
            stand_id=4, user_id=2, booking_date=self.future
        )
        before = Booking.objects.count()
        response = self.post(self.future.isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Выбранный стенд уже забронирован на эту дату."
        )
        self.assertEqual(
            response.context["form"].non_field_errors(),
            ["Выбранный стенд уже забронирован на эту дату."],
        )
        self.assertEqual(Booking.objects.count(), before)

    def test_cancelled_booking_does_not_block_stand(self):
        Booking.objects.create(
            stand_id=4,
            user_id=2,
            booking_date=self.future,
            status=Booking.Status.CANCELLED,
        )
        response = self.post(self.future.isoformat())
        self.assertRedirects(response, "/bookings/")
        self.assertEqual(
            Booking.objects.active()
            .filter(stand_id=4, booking_date=self.future)
            .count(),
            1,
        )

    def test_completed_booking_does_not_block_stand(self):
        Booking.objects.create(
            stand_id=4,
            user_id=2,
            booking_date=self.future,
            status=Booking.Status.COMPLETED,
        )
        response = self.post(self.future.isoformat())
        self.assertRedirects(response, "/bookings/")

    def test_status_cannot_be_set_through_form(self):
        self.client.post(
            self.url,
            {
                "stand": 4,
                "user": 1,
                "booking_date": self.future.isoformat(),
                "status": "completed",
            },
        )
        self.assertEqual(
            Booking.objects.latest("pk").status, Booking.Status.ACTIVE
        )

    def test_released_stand_can_be_booked_after_cancel(self):
        booking = Booking.objects.create(
            stand_id=4, user_id=2, booking_date=self.future
        )
        self.assertContains(
            self.post(self.future.isoformat()), "уже забронирован"
        )
        booking.cancel()
        response = self.post(self.future.isoformat())
        self.assertRedirects(response, "/bookings/")


class BookingUpdateViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def setUp(self):
        self.today = timezone.localdate()
        self.future = self.today + timedelta(days=60)
        self.booking = Booking.objects.create(
            stand_id=4, user_id=1, booking_date=self.future
        )
        self.url = f"/bookings/{self.booking.pk}/edit/"

    def post(self, booking_date=None, stand=4, user=1):
        booking_date = booking_date or self.future
        return self.client.post(
            self.url,
            {
                "stand": stand,
                "user": user,
                "booking_date": booking_date.isoformat(),
            },
        )

    def test_get_shows_form_with_current_values(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/booking_form.html")
        self.assertContains(
            response, f"Редактирование бронирования №{self.booking.pk}"
        )
        self.assertContains(response, "Сохранить изменения")
        self.assertContains(response, f'value="{self.future.isoformat()}"')
        form = response.context["form"]
        self.assertEqual(form.instance, self.booking)
        self.assertEqual(form["stand"].value(), 4)

    def test_change_date_updates_same_record(self):
        before = Booking.objects.count()
        new_date = self.future + timedelta(days=7)
        response = self.post(new_date)
        self.assertRedirects(response, "/bookings/")
        self.assertEqual(Booking.objects.count(), before)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_date, new_date)

    def test_change_stand_updates_same_record(self):
        response = self.post(stand=2)
        self.assertRedirects(response, "/bookings/")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.stand_id, 2)

    def test_save_without_changes_does_not_conflict_with_itself(self):
        before = Booking.objects.count()
        response = self.post()
        self.assertRedirects(response, "/bookings/")
        self.assertEqual(Booking.objects.count(), before)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.ACTIVE)

    def test_past_date_is_rejected(self):
        response = self.post(self.today - timedelta(days=1))
        self.assertContains(
            response, "Нельзя создать бронирование на прошедшую дату."
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_date, self.future)

    def test_conflict_with_other_active_booking_is_rejected(self):
        other = Booking.objects.create(
            stand_id=2, user_id=2, booking_date=self.future
        )
        response = self.post(stand=2)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Выбранный стенд уже забронирован на эту дату."
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.stand_id, 4)
        other.refresh_from_db()
        self.assertEqual(other.stand_id, 2)

    def test_cancelled_booking_of_other_user_does_not_conflict(self):
        Booking.objects.create(
            stand_id=2,
            user_id=2,
            booking_date=self.future,
            status=Booking.Status.CANCELLED,
        )
        self.assertRedirects(self.post(stand=2), "/bookings/")

    def test_unknown_booking_returns_404(self):
        self.assertEqual(
            self.client.get("/bookings/999999/edit/").status_code, 404
        )
        self.assertEqual(
            self.client.post("/bookings/999999/edit/", {}).status_code, 404
        )

    def test_cancelled_and_completed_bookings_cannot_be_edited(self):
        # №1 завершено, №3 отменено.
        for pk in (1, 3):
            self.assertEqual(
                self.client.get(f"/bookings/{pk}/edit/").status_code, 404
            )

    def test_list_has_edit_links_for_active_only(self):
        response = self.client.get("/bookings/")
        self.assertContains(response, "/edit/")
        cancelled = self.client.get("/bookings/?status=cancelled")
        self.assertNotContains(cancelled, "/edit/")
        self.assertNotContains(cancelled, "/cancel/")


class BookingCancelViewTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_post_cancels_booking_and_keeps_record(self):
        response = self.client.post("/bookings/2/cancel/", follow=True)
        self.assertRedirects(response, "/bookings/")
        booking = Booking.objects.get(pk=2)
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertContains(response, "Бронирование №2 отменено.")

    def test_cancelled_booking_leaves_active_list(self):
        self.client.post("/bookings/2/cancel/")
        response = self.client.get("/bookings/")
        ids = [row["id"] for row in response.context["bookings"]]
        self.assertNotIn(2, ids)
        cancelled = self.client.get("/bookings/?status=cancelled")
        self.assertIn(
            2, [row["id"] for row in cancelled.context["bookings"]]
        )

    def test_get_is_not_allowed(self):
        response = self.client.get("/bookings/2/cancel/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(
            Booking.objects.get(pk=2).status, Booking.Status.ACTIVE
        )

    def test_repeated_cancel_returns_404(self):
        self.client.post("/bookings/2/cancel/")
        self.assertEqual(
            self.client.post("/bookings/2/cancel/").status_code, 404
        )

    def test_unknown_and_inactive_bookings_return_404(self):
        for pk in (999999, 1, 3):
            self.assertEqual(
                self.client.post(f"/bookings/{pk}/cancel/").status_code,
                404,
                pk,
            )

    def test_cancel_releases_stand(self):
        future = timezone.localdate() + timedelta(days=90)
        booking = Booking.objects.create(
            stand_id=4, user_id=1, booking_date=future
        )
        data = {"stand": 4, "user": 2, "booking_date": future.isoformat()}
        busy = self.client.post("/bookings/create/", data)
        self.assertEqual(busy.status_code, 200)
        self.client.post(f"/bookings/{booking.pk}/cancel/")
        free = self.client.post("/bookings/create/", data)
        self.assertRedirects(free, "/bookings/")


class CsrfProtectionTests(TestCase):
    fixtures = ["tradestands.json"]

    def setUp(self):
        # Клиент с включённой проверкой CSRF, как в браузере.
        self.client = Client(enforce_csrf_checks=True)

    def test_post_without_token_is_forbidden(self):
        future = timezone.localdate() + timedelta(days=30)
        response = self.client.post(
            "/bookings/create/",
            {"stand": 4, "user": 1, "booking_date": future.isoformat()},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.client.post("/bookings/2/cancel/").status_code, 403
        )
        self.assertEqual(
            Booking.objects.get(pk=2).status, Booking.Status.ACTIVE
        )

    def test_forms_contain_csrf_token(self):
        for url in ("/bookings/create/", "/bookings/2/edit/", "/bookings/"):
            response = self.client.get(url)
            self.assertContains(
                response, "csrfmiddlewaretoken", msg_prefix=url
            )

    def test_post_with_token_is_accepted(self):
        response = self.client.get("/bookings/create/")
        token = response.cookies["csrftoken"].value
        future = timezone.localdate() + timedelta(days=30)
        response = self.client.post(
            "/bookings/create/",
            {
                "stand": 4,
                "user": 1,
                "booking_date": future.isoformat(),
                "csrfmiddlewaretoken": token,
            },
        )
        self.assertEqual(response.status_code, 302)


class FormNavigationTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_named_urls(self):
        self.assertEqual(
            reverse("bookings:booking_create"), "/bookings/create/"
        )
        self.assertEqual(
            reverse("bookings:booking_update", args=[5]),
            "/bookings/5/edit/",
        )
        self.assertEqual(
            reverse("bookings:booking_cancel", args=[5]),
            "/bookings/5/cancel/",
        )

    def test_list_links_to_create_form(self):
        response = self.client.get("/bookings/")
        self.assertContains(response, 'href="/bookings/create/"')
        self.assertContains(response, 'action="/bookings/2/cancel/"')

    def test_existing_routes_still_work(self):
        for url in ("/bookings/", "/bookings/1/", "/bookings/statistics/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
