from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Stand(models.Model):
    """Торговый стенд, доступный для аренды."""

    class StandType(models.TextChoices):
        STANDARD = "Стандарт", "Стандарт"
        PREMIUM = "Премиум", "Премиум"
        ISLAND = "Остров", "Остров"

    # Название стенда.
    name = models.CharField(
        max_length=200,
        verbose_name="Название стенда",
    )

    # Площадь в квадратных метрах: положительное число.
    area = models.FloatField(
        validators=[MinValueValidator(0.01)],
        verbose_name="Площадь, кв.м",
    )

    # Тип стенда: значение из заранее заданного набора.
    stand_type = models.CharField(
        max_length=50,
        choices=StandType.choices,
        default=StandType.STANDARD,
        verbose_name="Тип стенда",
    )

    def is_available_on(self, booking_date):
        """Проверить, свободен ли стенд на дату.

        Отменённые бронирования стенд не блокируют.
        """
        return not self.bookings.filter(
            booking_date=booking_date,
            is_cancelled=False,
        ).exists()

    def __str__(self):
        # Текстовое представление в админке, shell и т.п.
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Стенд"
        verbose_name_plural = "Стенды"
        constraints = [
            # Ограничение на уровне базы данных, как и в схеме ПР7.
            models.CheckConstraint(
                condition=Q(area__gt=0),
                name="stand_area_positive",
            ),
        ]
