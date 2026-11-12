from django.core.exceptions import ValidationError
from django.test import TestCase

from users.models import User


class UserModelTests(TestCase):
    fixtures = ["tradestands.json"]

    def test_str_and_ordering(self):
        self.assertEqual(
            [str(u) for u in User.objects.all()],
            ["Анна Смирнова", "Иван Петров", "ООО «Сладкий мир»"],
        )

    def test_email_is_validated(self):
        user = User(name="Тест", email="не-почта")
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn("email", ctx.exception.message_dict)

    def test_reverse_relation_to_bookings(self):
        user = User.objects.get(pk=2)
        self.assertEqual(user.bookings.count(), 3)
        self.assertEqual(user.bookings.active().count(), 3)
