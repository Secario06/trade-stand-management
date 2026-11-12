from django.db import models


class User(models.Model):
    """Арендатор торгового стенда.

    Это пользователь предметной области, а не встроенная модель
    аутентификации Django (django.contrib.auth).
    """

    # Имя арендатора или название организации.
    name = models.CharField(
        max_length=200,
        verbose_name="Имя арендатора",
    )

    # Электронная почта: EmailField проверяет формат адреса.
    email = models.EmailField(
        verbose_name="Электронная почта",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Арендатор"
        verbose_name_plural = "Арендаторы"
