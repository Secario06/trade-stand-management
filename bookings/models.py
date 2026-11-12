from django.db import models
from django.db.models import Q

from stands.models import Stand
from users.models import User


class Booking(models.Model):
    """Бронирование торгового стенда арендатором на дату."""

    # Стенд, для которого оформлено бронирование.
    # PROTECT запрещает удалять стенд, на который есть ссылки:
    # история бронирований сохраняется.
    stand = models.ForeignKey(
        Stand,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Стенд",
    )

    # Арендатор, оформивший бронирование.
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="Арендатор",
    )

    # Дата бронирования: DateField хранит дату, а не строку.
    booking_date = models.DateField(
        verbose_name="Дата бронирования",
    )

    # Признак отмены. Новое бронирование по умолчанию активно.
    is_cancelled = models.BooleanField(
        default=False,
        verbose_name="Бронирование отменено",
    )

    def cancel(self):
        """Отменить бронирование и сохранить изменение."""
        self.is_cancelled = True
        self.save(update_fields=["is_cancelled"])

    def is_active(self):
        """Проверить, активно ли бронирование."""
        return not self.is_cancelled

    def __str__(self):
        return f"{self.stand} — {self.booking_date} ({self.user})"

    class Meta:
        # Сначала по дате, затем по идентификатору.
        ordering = ["booking_date", "pk"]
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        constraints = [
            # Правило предметной области (ПР3, ПР7): на одну дату
            # у стенда не может быть двух активных бронирований.
            # Отменённые бронирования правило не затрагивают.
            models.UniqueConstraint(
                fields=["stand", "booking_date"],
                condition=Q(is_cancelled=False),
                name="unique_active_booking_per_stand_date",
            ),
        ]
