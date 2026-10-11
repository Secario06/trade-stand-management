from django.test import SimpleTestCase, override_settings


class HomepageTests(SimpleTestCase):
    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "торговыми стендами")
        self.assertContains(response, "bootstrap")
        self.assertContains(response, 'href="/stands/"')
        self.assertContains(response, 'href="/bookings/"')

    @override_settings(DEBUG=False)
    def test_custom_404_page(self):
        response = self.client.get("/nonexistent/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response, "404 – страница не найдена", status_code=404
        )
