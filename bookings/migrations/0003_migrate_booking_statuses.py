from django.db import migrations


def migrate_booking_statuses(apps, schema_editor):
    # Историческая модель, соответствующая состоянию БД на момент миграции.
    Booking = apps.get_model("bookings", "Booking")

    # Сохраняем сведения об отменённых бронированиях.
    Booking.objects.filter(is_cancelled=True).update(status="cancelled")

    # Все остальные существующие бронирования считаем активными.
    # Статус «завершено» по прошедшей дате автоматически не присваивается:
    # для этого нужно отдельное бизнес-правило.
    Booking.objects.filter(is_cancelled=False).update(status="active")


def reverse_booking_statuses(apps, schema_editor):
    Booking = apps.get_model("bookings", "Booking")

    # При откате восстанавливаем булев признак отмены.
    Booking.objects.filter(status="cancelled").update(is_cancelled=True)
    Booking.objects.exclude(status="cancelled").update(is_cancelled=False)


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0002_booking_status"),
    ]

    operations = [
        migrations.RunPython(
            migrate_booking_statuses,
            reverse_booking_statuses,
        ),
    ]
