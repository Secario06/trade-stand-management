from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from bookings.models import Booking
from stands.models import Stand

# Тестовая учётная запись создаётся только во временной тестовой базе.
TEST_PASSWORD = "test-only-password-123"


class AdminBase(TestCase):
    fixtures = ["tradestands.json"]

    def setUp(self):
        super().setUp()
        auth_user = get_user_model()
        self.superuser = auth_user.objects.create_superuser(
            "admin", "admin@example.com", TEST_PASSWORD
        )
        self.client.force_login(self.superuser)

    @staticmethod
    def result_ids(response):
        return [obj.pk for obj in response.context["cl"].result_list]


class AdminAccessTests(AdminBase):
    def test_login_required(self):
        self.client.logout()
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_index_shows_russian_application_and_model_names(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        for text in (
            "Торговые стенды",
            "Арендаторы",
            "Бронирования",
            "Стенды",
            "Управление данными",
            "Торговые стенды: администрирование",
        ):
            self.assertContains(response, text)

    def test_domain_models_are_registered_once(self):
        from django.contrib import admin

        for model in (Stand, Booking):
            self.assertIn(model, admin.site._registry)
        from users.models import User as TenantUser

        self.assertIn(TenantUser, admin.site._registry)


class StandAdminTests(AdminBase):
    url = "/admin/stands/stand/"

    def test_changelist_columns(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in (
            "Активных бронирований",
            "Страница на сайте",
            "Большой стенд",
            "Тип стенда",
        ):
            self.assertContains(response, text)

    def test_default_ordering_by_name(self):
        response = self.client.get(self.url)
        self.assertEqual(self.result_ids(response), [1, 2, 3, 4])

    def test_search_by_name(self):
        response = self.client.get(self.url, {"q": "павильон"})
        self.assertEqual(self.result_ids(response), [1, 2])

    def test_filter_by_type_and_large_flag(self):
        by_type = self.client.get(self.url, {"stand_type__exact": "Премиум"})
        self.assertEqual(self.result_ids(by_type), [3])
        large = self.client.get(self.url, {"is_large__exact": "1"})
        self.assertEqual(self.result_ids(large), [3])

    def test_active_bookings_are_annotated(self):
        response = self.client.get(self.url)
        counts = {
            obj.pk: obj.active_bookings
            for obj in response.context["cl"].result_list
        }
        self.assertEqual(counts, {1: 2, 2: 2, 3: 2, 4: 1})

    def test_site_link_uses_get_absolute_url(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'href="/stands/pavilon-a-1/"')

    def test_area_is_editable_in_list(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="form-0-area"')
        data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "_save": "Сохранить",
        }
        areas = {1: 45.0, 2: 18.5, 3: 50.0, 4: 36.0}
        for index, pk in enumerate((1, 2, 3, 4)):
            data[f"form-{index}-id"] = str(pk)
            data[f"form-{index}-area"] = str(areas[pk])
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        stand = Stand.objects.get(pk=1)
        self.assertEqual(stand.area, 45.0)
        # Вычисляемое поле пересчитано базой данных.
        self.assertTrue(stand.is_large)

    def test_change_page_has_inline_bookings_and_readonly_fields(self):
        response = self.client.get(f"{self.url}1/change/")
        self.assertEqual(response.status_code, 200)
        # Встроенная таблица бронирований стенда (4 записи).
        self.assertContains(response, 'name="bookings-TOTAL_FORMS"')
        self.assertContains(response, 'value="4"')
        # slug и вычисляемое поле показываются без возможности правки.
        self.assertContains(response, "pavilon-a-1")
        self.assertNotContains(response, 'name="slug"')
        self.assertNotContains(response, 'name="is_large"')
        # Подсказка к полю площади.
        self.assertContains(response, "Площадь стенда в квадратных метрах")

    def test_view_on_site_link_opens_public_page(self):
        content_type = ContentType.objects.get_for_model(Stand)
        link = reverse("admin:view_on_site", args=(content_type.pk, 1))
        response = self.client.get(link)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].endswith("/stands/pavilon-a-1/"))

    def test_add_stand_creates_slug(self):
        data = {
            "name": "Новый павильон",
            "stand_type": "Стандарт",
            "area": "15",
            "bookings-TOTAL_FORMS": "0",
            "bookings-INITIAL_FORMS": "0",
            "bookings-MIN_NUM_FORMS": "0",
            "bookings-MAX_NUM_FORMS": "1000",
            "_save": "Сохранить",
        }
        response = self.client.post(f"{self.url}add/", data)
        self.assertEqual(response.status_code, 302)
        stand = Stand.objects.get(name="Новый павильон")
        self.assertEqual(stand.slug, f"novyi-pavilon-{stand.pk}")

    def test_stand_with_bookings_cannot_be_deleted(self):
        response = self.client.post(
            f"{self.url}1/delete/", {"post": "yes"}
        )
        # Удаление запрещено on_delete=PROTECT, стенд остаётся в базе.
        self.assertTrue(Stand.objects.filter(pk=1).exists())
        self.assertNotEqual(response.status_code, 500)


class UserAdminTests(AdminBase):
    url = "/admin/users/user/"

    def test_changelist_and_search_by_name_and_email(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        by_name = self.client.get(self.url, {"q": "сладкий"})
        self.assertEqual(self.result_ids(by_name), [2])
        by_email = self.client.get(self.url, {"q": "anna.smirnova"})
        self.assertEqual(self.result_ids(by_email), [3])

    def test_change_page_has_inline_bookings(self):
        response = self.client.get(f"{self.url}2/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="bookings-TOTAL_FORMS"')
        self.assertContains(response, 'value="3"')

    def test_bookings_total_column(self):
        response = self.client.get(self.url)
        totals = {
            obj.pk: obj.bookings_count
            for obj in response.context["cl"].result_list
        }
        self.assertEqual(totals, {1: 3, 2: 3, 3: 3})


class BookingAdminTests(AdminBase):
    url = "/admin/bookings/booking/"

    def test_changelist_shows_related_objects_and_area(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Павильон А")
        self.assertContains(response, "Иван Петров")
        self.assertContains(response, "Площадь, кв.м")
        self.assertContains(response, "Завершено")

    def test_default_ordering_is_newest_first(self):
        response = self.client.get(self.url)
        self.assertEqual(self.result_ids(response)[0], 9)

    def test_search_by_related_fields(self):
        by_user = self.client.get(self.url, {"q": "сладкий"})
        self.assertEqual(sorted(self.result_ids(by_user)), [2, 4, 7])
        by_stand = self.client.get(self.url, {"q": "премиум"})
        self.assertEqual(sorted(self.result_ids(by_stand)), [2, 5])

    def test_filter_by_status(self):
        for status, expected in (
            ("cancelled", [3]),
            ("completed", [1]),
        ):
            response = self.client.get(self.url, {"status__exact": status})
            self.assertEqual(self.result_ids(response), expected)
        active = self.client.get(self.url, {"status__exact": "active"})
        self.assertEqual(len(self.result_ids(active)), 7)

    def test_date_hierarchy(self):
        response = self.client.get(
            self.url,
            {
                "booking_date__year": "2026",
                "booking_date__month": "11",
            },
        )
        self.assertEqual(sorted(self.result_ids(response)), [6, 7, 8, 9])

    def test_related_objects_are_loaded_without_extra_queries(self):
        with CaptureQueriesContext(connection) as before:
            self.client.get(self.url)
        for day in range(1, 6):
            Booking.objects.create(
                stand_id=2,
                user_id=1,
                booking_date=date(2027, 3, day),
            )
        with CaptureQueriesContext(connection) as after:
            self.client.get(self.url)
        # Число запросов не растёт с числом строк (нет проблемы N+1).
        self.assertEqual(len(before), len(after))

    def test_cancel_action(self):
        response = self.client.post(
            self.url,
            {"action": "cancel_bookings", "_selected_action": [2, 4]},
            follow=True,
        )
        self.assertEqual(
            list(Booking.objects.filter(pk__in=[2, 4]).values_list(
                "status", flat=True)),
            ["cancelled", "cancelled"],
        )
        self.assertContains(response, "Отменено бронирований: 2.")

    def test_complete_action(self):
        self.client.post(
            self.url,
            {"action": "complete_bookings", "_selected_action": [2]},
        )
        self.assertEqual(
            Booking.objects.get(pk=2).status, Booking.Status.COMPLETED
        )

    def test_restore_action_returns_booking_to_active(self):
        response = self.client.post(
            self.url,
            {"action": "restore_bookings", "_selected_action": [3]},
            follow=True,
        )
        self.assertEqual(Booking.objects.get(pk=3).status, "active")
        self.assertContains(response, "Возвращено бронирований: 1.")

    def test_restore_action_respects_business_rule(self):
        # На дату отменённой брони стенд уже занят другой активной бронью.
        Booking.objects.get(pk=4).cancel()
        Booking.objects.create(
            stand_id=1, user_id=3, booking_date=date(2026, 10, 22)
        )
        response = self.client.post(
            self.url,
            {"action": "restore_bookings", "_selected_action": [4]},
            follow=True,
        )
        self.assertEqual(Booking.objects.get(pk=4).status, "cancelled")
        level = [m.level for m in response.context["messages"]]
        self.assertIn(messages.WARNING, level)
        self.assertContains(response, "Не возвращено из-за занятой даты: 1.")

    def test_admin_form_rejects_second_active_booking_for_same_date(self):
        data = {
            "stand": "3",
            "user": "1",
            "booking_date": "2026-10-15",
            "status": "active",
            "_save": "Сохранить",
        }
        response = self.client.post(f"{self.url}add/", data)
        # Форма не сохраняется и показывает ошибку, а не падает с 500.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "уже есть активное бронирование")
        self.assertEqual(Booking.objects.count(), 9)

    def test_admin_form_allows_cancelled_booking_for_busy_date(self):
        data = {
            "stand": "3",
            "user": "1",
            "booking_date": "2026-10-15",
            "status": "cancelled",
            "_save": "Сохранить",
        }
        response = self.client.post(f"{self.url}add/", data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Booking.objects.count(), 10)

    def test_status_change_in_admin_form(self):
        data = {
            "stand": "1",
            "user": "2",
            "booking_date": "2026-10-22",
            "status": "completed",
            "_save": "Сохранить",
        }
        response = self.client.post(f"{self.url}4/change/", data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Booking.objects.get(pk=4).status, "completed")


class AdminPermissionsTests(TestCase):
    """Группа с ограниченными правами: просмотр, добавление, изменение."""

    fixtures = ["tradestands.json"]

    def make_staff(self, username, codenames):
        auth_user = get_user_model()
        staff = auth_user.objects.create_user(
            username, password=TEST_PASSWORD, is_staff=True
        )
        staff.user_permissions.set(
            Permission.objects.filter(codename__in=codenames)
        )
        return staff

    def test_staff_without_permissions_sees_nothing(self):
        self.client.force_login(self.make_staff("nobody", []))
        response = self.client.get("/admin/stands/stand/")
        self.assertEqual(response.status_code, 403)

    def test_operator_can_view_add_and_change_but_not_delete(self):
        self.client.force_login(
            self.make_staff(
                "operator", ["view_stand", "add_stand", "change_stand"]
            )
        )
        self.assertEqual(
            self.client.get("/admin/stands/stand/").status_code, 200
        )
        self.assertEqual(
            self.client.get("/admin/stands/stand/add/").status_code, 200
        )
        self.assertEqual(
            self.client.get("/admin/stands/stand/1/change/").status_code, 200
        )
        # Удаление недоступно.
        self.assertEqual(
            self.client.get("/admin/stands/stand/4/delete/").status_code,
            403,
        )
        response = self.client.get("/admin/stands/stand/")
        self.assertNotContains(response, "delete_selected")

    def test_view_only_user_cannot_change(self):
        self.client.force_login(self.make_staff("viewer", ["view_stand"]))
        self.assertEqual(
            self.client.get("/admin/stands/stand/").status_code, 200
        )
        response = self.client.post(
            "/admin/stands/stand/1/change/",
            {"name": "Взлом", "area": "1", "stand_type": "Остров"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Stand.objects.get(pk=1).name, "Павильон А")

    def test_permissions_do_not_replace_business_rules(self):
        # Даже полные права не позволяют обойти on_delete=PROTECT.
        superuser = get_user_model().objects.create_superuser(
            "boss", "b@example.com", TEST_PASSWORD
        )
        self.client.force_login(superuser)
        self.client.post("/admin/stands/stand/3/delete/", {"post": "yes"})
        self.assertTrue(Stand.objects.filter(pk=3).exists())
