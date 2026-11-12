from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from bookings.models import Booking
from homepage import views
from stands.models import Stand


class HomepageTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "торговыми стендами")
        self.assertContains(response, "bootstrap")
        self.assertContains(response, 'href="/stands/"')
        self.assertContains(response, 'href="/bookings/"')

    def test_index_uses_templates_with_inheritance(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "homepage/index.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "includes/navigation.html")

    def test_page_helper_is_removed(self):
        self.assertFalse(hasattr(views, "page"))

    @override_settings(DEBUG=False)
    def test_custom_404_page(self):
        response = self.client.get("/nonexistent/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(
            response, "404 – страница не найдена", status_code=404
        )


class NamespaceTests(SimpleTestCase):
    def test_named_urls_with_namespaces(self):
        self.assertEqual(reverse("homepage:index"), "/")
        self.assertEqual(reverse("stands:list"), "/stands/")
        self.assertEqual(
            reverse("stands:detail", kwargs={"slug": "pavilon-a-1"}),
            "/stands/pavilon-a-1/",
        )
        self.assertEqual(reverse("bookings:bookings"), "/bookings/")
        self.assertEqual(
            reverse("bookings:detail", args=[1]), "/bookings/1/"
        )


class StaticFilesTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_static_files_are_found(self):
        for path in (
            "homepage/css/style.css",
            "homepage/js/main.js",
            "homepage/img/logo.png",
        ):
            self.assertIsNotNone(finders.find(path), path)

    def test_base_template_links_static_files(self):
        response = self.client.get("/")
        self.assertContains(response, "/static/homepage/css/style.css")
        self.assertContains(response, "/static/homepage/js/main.js")
        self.assertContains(response, "/static/homepage/img/logo.png")
        self.assertContains(response, 'id="current-year"')


class ContextProcessorTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_common_data_is_available_on_every_page(self):
        for url in ("/", "/stands/", "/bookings/", "/bookings/statistics/"):
            response = self.client.get(url)
            self.assertEqual(
                response.context["site_name"], "Торговые стенды", url
            )
            self.assertEqual(response.context["stands_count"], 4, url)

    def test_data_is_used_in_base_template(self):
        response = self.client.get("/")
        self.assertContains(response, "<title>")
        self.assertContains(response, "Стенды (4)")

    def test_count_reflects_database(self):
        Stand.objects.create(name="Новый стенд", area=10)
        response = self.client.get("/stands/")
        self.assertEqual(response.context["stands_count"], 5)
        self.assertContains(response, "Стенды (5)")

    def test_status_enum_is_available_in_templates(self):
        response = self.client.get("/")
        self.assertIs(response.context["BookingStatus"], Booking.Status)

    def test_view_does_not_pass_common_data_manually(self):
        # Представление главной страницы не формирует контекст вручную,
        # общие данные добавляет контекстный процессор.
        self.assertEqual(self.client.get("/").context["stands_count"], 4)
