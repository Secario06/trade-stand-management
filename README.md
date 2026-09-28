# Система управления торговыми стендами

Консольное приложение для учёта торговых стендов и управления их бронированием.
Реализовано в объектно-ориентированном стиле (ПР3).

## Классы

### Stand (Торговый стенд)
- Атрибуты: `id`, `name`, `area`, `stand_type`
- Методы: `__str__()`, `validate_area()` (staticmethod), `from_data()` (classmethod), `to_data()`

### User (Арендатор)
- Атрибуты: `id`, `name`, `email`
- Методы: `__str__()`, `from_data()` (classmethod), `to_data()`

### Booking (Бронирование)
- Атрибуты: `id`, `stand` (объект Stand), `booking_date`, `user` (объект User), `is_cancelled`
- Методы: `cancel()`, `is_active()`, `__str__()`

## Взаимодействие объектов
`Booking` хранит ссылки на объекты `Stand` и `User`, а не их идентификаторы:
```python
booking.stand.name
booking.user.email