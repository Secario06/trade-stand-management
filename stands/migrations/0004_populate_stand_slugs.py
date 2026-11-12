from django.db import migrations
from django.utils.text import slugify
from unidecode import unidecode


def populate_stand_slugs(apps, schema_editor):
    # Историческая модель, соответствующая состоянию БД на момент миграции.
    Stand = apps.get_model("stands", "Stand")

    # Стабильный порядок обработки.
    for stand in Stand.objects.all().order_by("pk"):
        # Название транслитерируется в латиницу и приводится к виду URL.
        base_slug = slugify(unidecode(stand.name)) or "stand"

        # Первичный ключ в конце гарантирует уникальность slug.
        stand.slug = f"{base_slug}-{stand.pk}"

        # Сохраняется только изменяемое поле.
        stand.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("stands", "0003_stand_slug"),
    ]

    operations = [
        migrations.RunPython(
            populate_stand_slugs,
            migrations.RunPython.noop,
        ),
    ]
