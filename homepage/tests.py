from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from homepage import views


class HomepageTests(SimpleTestCase):
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
        self.assertEqual(reverse("stands:detail", args=[1]), "/stands/1/")
        self.assertEqual(reverse("bookings:bookings"), "/bookings/")
        self.assertEqual(
            reverse("bookings:detail", args=[1]), "/bookings/1/"
        )


class StaticFilesTests(SimpleTestCase):
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
