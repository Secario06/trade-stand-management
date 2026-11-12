# Система управления торговыми стендами

Система учёта торговых стендов и их бронирования на Python с веб-интерфейсом на Django. Доступ к данным выполняется через Django ORM, база данных – SQLite.

## 1. Назначение проекта

Приложение для управления торговыми стендами и их бронированием. Проект позволяет хранить сведения о стендах, арендаторах и бронированиях, выполнять основные операции с этими объектами и просматривать информацию через веб-интерфейс Django.

Проект развивался поэтапно: консольная версия (ПР3), веб-интерфейс на Django (ПР5), шаблоны (ПР6), база данных SQLite и SQL (ПР7). В ПР9 слой данных переведён с ручных SQL-запросов и `sqlite3` на Django ORM.

## 2. Используемые технологии

- Python 3;
- Django 5.2 (ORM, миграции, шаблоны);
- SQLite (база Django `db.sqlite3`);
- HTML5, CSS3, JavaScript, Bootstrap 5.3 (через CDN);
- JSON (консольная версия), Git, pytest, flake8.

## 3. Предметная область

Основные сущности: стенд, арендатор, бронирование. Арендатор может бронировать стенды на определённые даты. Один стенд не может иметь два активных бронирования на одну дату; отменённое бронирование стенд не блокирует.

## 4. Модели данных

Модели находятся в `models.py` соответствующих Django-приложений. Это отдельные классы Django, не путать с обычными классами консольной версии в пакете `models/`.

| Модель | Приложение | Поля |
|--------|------------|------|
| `Stand` – стенд | `stands` | `name` (CharField), `area` (FloatField, > 0), `stand_type` (CharField с выбором: Стандарт, Премиум, Остров) |
| `User` – арендатор | `users` | `name` (CharField), `email` (EmailField) |
| `Booking` – бронирование | `bookings` | `stand` (ForeignKey), `user` (ForeignKey), `booking_date` (DateField), `is_cancelled` (BooleanField, по умолчанию `False`) |

Первичные ключи `id` создаются Django автоматически. Модель `User` описывает арендатора предметной области и не является встроенной моделью аутентификации `django.contrib.auth`.

### Связи между моделями

- `Booking.stand` → `Stand`, `Booking.user` → `User` (связь «многие к одному»);
- `on_delete=models.PROTECT`: нельзя удалить стенд или арендатора, на которых есть бронирования (сохраняется история);
- `related_name="bookings"`: у стенда и арендатора доступно `stand.bookings.all()` и `user.bookings.all()`;
- в таблице столбцы называются `stand_id` и `user_id` (`booking.stand_id`).

### Методы и ограничения

- `Stand.is_available_on(date)` – свободен ли стенд на дату (отменённые брони не учитываются);
- `Booking.cancel()` – отмена бронирования с сохранением (`save(update_fields=["is_cancelled"])`);
- `CheckConstraint`: площадь стенда больше нуля;
- `UniqueConstraint` с условием `is_cancelled=False`: не более одного активного бронирования стенда на дату (правило предметной области, как в ПР7);
- `Meta.ordering`, `verbose_name`, `__str__()` у всех моделей; модели зарегистрированы в админке.

## 5. Миграции и база данных

Структура базы управляется миграциями (`stands/migrations`, `users/migrations`, `bookings/migrations`), они хранятся в Git.

```text
python manage.py makemigrations     # создать миграции по моделям
python manage.py showmigrations     # состояние миграций
python manage.py sqlmigrate bookings 0001   # посмотреть SQL миграции
python manage.py migrate            # применить миграции
python manage.py makemigrations --check     # нет ли неучтённых изменений
```

Используются две базы:

- `db.sqlite3` – **целевая** база Django (`DATABASES`), с ней работает ORM; в репозиторий не входит;
- `data/tradestands.sqlite` – **исходная** база ПР7, остаётся без изменений и служит источником данных при переносе.

Выбрана стратегия «новые таблицы, управляемые Django, и перенос данных»: прежние таблицы не подключались через `db_table`, миграции к ним не применялись.

### Перенос данных

1. Исследовать исходную базу: `python db/inspect_source_db.py` (таблицы, столбцы, число записей, целостность ссылок).
2. Применить миграции: `python manage.py migrate`.
3. Перенести данные: `python db/import_sqlite_to_orm.py`.

Скрипт читает исходную базу только на чтение, переносит стенды и арендаторов, затем бронирования с сохранением идентификаторов и связей, преобразует строки дат в `date`, работает в одной транзакции (`transaction.atomic()`) и безопасен при повторном запуске (`update_or_create`). Перенесено: 4 стенда, 3 арендатора, 5 бронирований.

### Fixture

Для наполнения базы без исходной базы ПР7 есть fixture `fixtures/tradestands.json` (3 арендатора, 4 стенда, 9 бронирований; бронирования №6–9 добавлены через ORM для демонстрации пагинации):

```text
python manage.py loaddata tradestands.json
python manage.py dumpdata users stands bookings --indent 2 --output fixtures/tradestands.json
```

## 6. Операции ORM

Реализовано более 15 различных ORM-выражений.

| Направление | Примеры в проекте |
|-------------|-------------------|
| Получение | `Stand.objects.all()`, `get_object_or_404(Stand, pk=…)`, `get_object_or_404(Booking.objects.select_related("stand", "user"), pk=…)` |
| Фильтрация | `filter(area__gte=…)`; цепочка `filter(booking_date=…)`, `filter(stand_id=…)`, `filter(user_id=…)`; по связанному полю `filter(stand__stand_type=…)`; `exclude(is_cancelled=True)`; `Stand.objects.exclude(pk__in=…)` |
| Поиск | `filter(name__icontains=…)`; поиск по нескольким полям связанных моделей через `Q(stand__name__icontains) \| Q(user__name__icontains) \| Q(user__email__icontains)` |
| Сортировка | `order_by("name")`; `order_by(SORT_FIELDS[sort], "id")` (допустимые поля из словаря, в том числе `stand__name`, `user__name`); `order_by("-bookings_count", "name")` |
| Связи | обратная связь `stand.bookings.select_related("user")`; `annotate(stand_name=F("stand__name"))` + `values()`; `values_list("stand_id", flat=True)` |
| Агрегирование | `aggregate(Count, Min, Max, Avg, Sum)`; `annotate(bookings_count=Count("bookings", filter=Q(bookings__is_cancelled=False)))`; `values("stand_type").annotate(...)`; фильтр по агрегату `filter(bookings_count__gt=1)`; `.count()` |
| Срез | `order_by("-pk")[:3]` |
| Пагинация | `Paginator(bookings, 5).get_page(...)`, ссылки `{% querystring page=… %}` |
| CRUD | `create()`, `save()`, `delete()`, `get_or_create()`, `update_or_create()` (shell, перенос данных, тесты) |

Поиск по кириллице: встроенный `LIKE` в SQLite не учитывает регистр только для латиницы, поэтому `tradestands/sqlite_unicode.py` подключает Unicode-aware функцию `like()` (регистрируется в `stands/apps.py`), и `icontains` находит «павильон» в названии «Павильон А».

## 7. Веб-интерфейс

| URL | Имя маршрута | Данные |
|-----|--------------|--------|
| `/` | `homepage:index` | – |
| `/stands/` | `stands:list` | стенды; поиск `?q=`, площадь `?min_area=` |
| `/stands/<id>/` | `stands:detail` | стенд, занятость на дату `?date=`, история бронирований |
| `/stands/available/` | `stands:available` | стенды, свободные на дату `?date=` |
| `/bookings/` | `bookings:bookings` | бронирования: фильтры `date`, `stand`, `user`, `type`, `q`, `show=all`; сортировка `sort` (`date`, `stand`, `user`); пагинация `page` (по 5) |
| `/bookings/<id>/` | `bookings:detail` | бронирование со стендом и арендатором (`select_related`) |
| `/bookings/statistics/` | `bookings:statistics` | агрегаты, группировка, фильтр по агрегату, последние бронирования |

Обработка ошибок: несуществующий объект даёт ответ 404 (`get_object_or_404`), некорректные параметры фильтров, даты и номера страницы не приводят к ошибке (сообщение или значение по умолчанию), пустые выборки показывают сообщение. Имена URL, шаблоны, навигация и оформление сохранены.

## 8. Структура проекта

```text
проект фреймворк/
├── stands/        # модель Stand, представления стендов, admin, тесты
├── users/         # модель User (арендатор), admin, тесты
├── bookings/      # модель Booking, список/карточка/статистика, тесты
├── homepage/      # главная, 404, статические файлы
├── templates/     # base.html, 404.html, includes/navigation.html
├── fixtures/      # tradestands.json (dumpdata/loaddata)
├── tradestands/   # настройки, urls, sqlite_unicode.py, тесты проекта
├── db/            # скрипты: перенос в ORM, инспекция, модуль SQL-слоя ПР7
├── sql/           # schema.sql, queries.sql (SQL-слой ПР7)
├── data/          # tradestands.sqlite (исходная база ПР7), JSON
├── models/, tests/, legacy/   # консольная версия и её тесты
├── main.py, storage.py, utils.py, manage.py
└── README.md
```

Файлы SQL-слоя ПР7 (`sql/schema.sql`, `sql/queries.sql`, `db/database.py`, `db/import_json.py`) сохранены как предыдущая реализация; веб-представления их больше не используют. Консольная версия (`main.py`) продолжает работать с JSON.

## 9. Запуск проекта

```text
git clone <адрес репозитория>
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata tradestands.json
python manage.py runserver
```

Открыть `http://127.0.0.1:8000/`. Данные также можно перенести из исходной базы ПР7: `python db/import_sqlite_to_orm.py` (вместо `loaddata`). При `DEBUG = False` сервер разработки не раздаёт статику: используйте `python manage.py runserver --insecure` или включите `DEBUG = True`.

Консольная версия: `python main.py`.

## 10. Проверка

```text
python manage.py check
python manage.py showmigrations
python manage.py makemigrations --check
python manage.py test        # тесты моделей, ORM-запросов, страниц, переноса данных
pytest -v                    # тесты консольной версии и SQL-слоя ПР7
flake8 . --extend-exclude=venv
```

Файл `db.sqlite3` не хранится в репозитории (после клонирования таблицы создаются миграциями, данные загружаются fixture).

## 11. Текущее состояние и планы

Реализовано: модели и связи, миграции, перенос данных из базы ПР7, чтение данных через ORM, фильтрация, поиск, сортировка, пагинация, статистика, тесты.

Не реализовано: формы Django и создание/изменение/отмена бронирований через веб-интерфейс, аутентификация и API – следующие этапы.

## Автор

Манукян Андрей Сержикович, ЭФБО-11-24.
