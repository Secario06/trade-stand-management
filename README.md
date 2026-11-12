# Система управления торговыми стендами

Система учёта торговых стендов и их бронирования на Python с веб-интерфейсом на Django. Доступ к данным выполняется через Django ORM, база данных – SQLite, управление данными – через административную панель Django.

## 1. Назначение проекта

Приложение для управления торговыми стендами и их бронированием. Проект позволяет хранить сведения о стендах, арендаторах и бронированиях, выполнять основные операции с этими объектами, просматривать информацию в веб-интерфейсе и управлять данными в Django Admin.

Проект развивался поэтапно: консольная версия (ПР3), веб-интерфейс и шаблоны Django (ПР5–ПР6), SQL и SQLite (ПР7), Django ORM и миграции (ПР9). В ПР10 настроена административная панель, статусы бронирований переведены на `TextChoices`, добавлены менеджер `QuerySet`, `slug` и `get_absolute_url()`, вычисляемое поле `GeneratedField`, контекстные процессоры и анализ SQL в Django Debug Toolbar.

## 2. Используемые технологии

- Python 3, Django 5.2 (ORM, миграции, админка, шаблоны);
- SQLite (база Django `db.sqlite3`);
- Unidecode – транслитерация названий в `slug`;
- django-debug-toolbar – анализ SQL-запросов при разработке;
- HTML5, CSS3, JavaScript, Bootstrap 5.3 (через CDN);
- Git, pytest, flake8.

## 3. Предметная область

Основные сущности: стенд, арендатор, бронирование. Арендатор бронирует стенды на определённые даты. Бронирование имеет статус: **активно**, **отменено** или **завершено**. Правила:

- стенд занимает **только активное** бронирование; отменённые и завершённые бронирования стенд не блокируют;
- на одну дату у стенда не может быть двух активных бронирований;
- отмена и завершение не удаляют запись (сохраняется история).

## 4. Модели данных

| Модель | Приложение | Поля |
|--------|------------|------|
| `Stand` – стенд | `stands` | `name`, `area` (> 0), `stand_type` (Стандарт, Премиум, Остров), `slug`, `is_large` |
| `User` – арендатор | `users` | `name`, `email` |
| `Booking` – бронирование | `bookings` | `stand` (FK), `user` (FK), `booking_date`, `status` |

Модель `users.User` описывает арендатора предметной области и не является встроенной моделью аутентификации Django. Суперпользователь Django (вход в админку) и арендатор – разные сущности.

**Связи.** `Booking.stand` и `Booking.user` – `ForeignKey` с `on_delete=PROTECT` (стенд или арендатора с бронированиями удалить нельзя) и `related_name="bookings"` (`stand.bookings`, `user.bookings`).

**Статусы бронирования.** `Booking.Status` (`TextChoices`): `ACTIVE` («Активно»), `CANCELLED` («Отменено»), `COMPLETED` («Завершено»). В коде статусы сравниваются с константами `Booking.Status`, а не со строками. Методы `cancel()`, `complete()`, `is_active()`.

**Менеджер и QuerySet.** `BookingQuerySet` с методами `active()`, `cancelled()`, `completed()`, `for_date(date)` и менеджер `BookingManager` (`Booking.objects`). `Booking.objects.all()` возвращает все записи, включая отменённые; фильтрация выполняется только при явном вызове методов. Методы можно объединять: `Booking.objects.active().for_date(d)`.

**slug и адрес стенда.** `Stand.slug` (`SlugField`, уникальный, не редактируется вручную) формируется при сохранении: название транслитерируется (`unidecode`), приводится к виду URL и дополняется первичным ключом, например `pavilon-a-1`. Метод `get_absolute_url()` возвращает адрес через `reverse("stands:detail", kwargs={"slug": ...})`; его используют шаблоны и ссылка «Смотреть на сайте» в админке.

**GeneratedField.** `Stand.is_large` – вычисляемое поле (`db_persist=True`): стенд большой, если площадь не меньше 40 кв.м. Значение вычисляет и пересчитывает база данных, вручную оно не задаётся.

**Ограничения.** `CheckConstraint` (площадь > 0); `UniqueConstraint` с условием `status="active"` – не более одного активного бронирования стенда на дату (в формах и админке показывается сообщение об ошибке).

## 5. Миграции и база данных

```text
python manage.py makemigrations     # создать миграции по моделям
python manage.py showmigrations     # состояние миграций
python manage.py sqlmigrate bookings 0004   # SQL миграции
python manage.py migrate            # применить миграции
python manage.py makemigrations --check     # нет ли неучтённых изменений
```

Миграции хранятся в Git. Основные шаги ПР10:

- `bookings 0002` – поле `status`; `0003` – **миграция данных** (`is_cancelled` → `status`: отменённые получают `cancelled`, остальные `active`, обратная операция предусмотрена); `0004` – удаление `is_cancelled` и замена ограничения уникальности на условие по статусу;
- `stands 0002` – `GeneratedField` `is_large` и `help_text`; `0003` – поле `slug`; `0004` – **миграция данных** (заполнение `slug` у существующих стендов); `0005` – уникальность `slug`.

Данные ПР7 переносятся из `data/tradestands.sqlite` в базу Django скриптом `python db/import_sqlite_to_orm.py` (исходная база не изменяется). Для наполнения базы без неё есть fixture:

```text
python manage.py loaddata tradestands.json
python manage.py dumpdata users stands bookings --indent 2 --output fixtures/tradestands.json
```

## 6. Операции ORM

| Направление | Примеры в проекте |
|-------------|-------------------|
| Получение | `Stand.objects.all()`, `get_object_or_404(Stand, slug=…)`, `get_object_or_404(Booking.objects.select_related("stand", "user"), pk=…)` |
| Фильтрация | `filter(area__gte=…)`; `Booking.objects.active().for_date(…)`; цепочка по дате, стенду, арендатору; по связанному полю `filter(stand__stand_type=…)`; `Stand.objects.exclude(pk__in=…)` |
| Поиск | `icontains`; `Q(name__icontains) \| Q(area=…)`; поиск по полям связанных моделей `Q(stand__name__icontains) \| Q(user__name__icontains) \| Q(user__email__icontains)` |
| Сортировка | `order_by(SORT_FIELDS[sort], "pk")` с разрешёнными полями (в том числе `stand__name`, `user__name`) и направлением; `order_by("-bookings_count", "name")` |
| Связи | `stand.bookings.select_related("user")`; `annotate(stand_name=F("stand__name"))` + `values()`; `values_list("stand_id", flat=True)` |
| Агрегирование | `aggregate(Count, Min, Max, Avg, Sum)` и `Count("id", filter=Q(status=…))` по статусам; `annotate(Count("bookings", filter=Q(...)))`; `values().annotate()`; фильтр по агрегату `filter(bookings_count__gt=1)` |
| Срез, пагинация | `order_by("-pk")[:3]`; `Paginator(…, 5)` и `{% querystring page=… %}` |

Поиск по кириллице: `tradestands/sqlite_unicode.py` подключает Unicode-aware функцию `like()`, поэтому `icontains` находит «павильон» в названии «Павильон А».

**Оптимизация запросов.** Список бронирований получает названия стенда и арендатора одним запросом (`annotate(F())` + `values()`), карточка бронирования – `select_related("stand", "user")`; на странице списка выполняется 5 запросов (подсчёт для пагинации, число стендов для навигации, списки стендов и арендаторов, страница записей), на карточке – 2.

## 7. Веб-интерфейс

| URL | Имя маршрута | Данные |
|-----|--------------|--------|
| `/` | `homepage:index` | – |
| `/stands/` | `stands:list` | стенды; поиск `?q=`, площадь `?min_area=`, сортировка `?sort=name\|area&direction=asc\|desc` |
| `/stands/<slug>/` | `stands:detail` | стенд, занятость на дату `?date=`, история бронирований |
| `/stands/available/` | `stands:available` | стенды, свободные на дату (учитываются только активные бронирования) |
| `/bookings/` | `bookings:bookings` | фильтры `status` (active по умолчанию, cancelled, completed, all), `date`, `stand`, `user`, `type`, `q`; сортировка `sort`; пагинация `page` |
| `/bookings/<id>/` | `bookings:detail` | бронирование со стендом и арендатором |
| `/bookings/statistics/` | `bookings:statistics` | показатели по статусам, агрегаты, группировки, последние бронирования |
| `/admin/` | – | административная панель |

Несуществующий объект даёт ответ 404, некорректные параметры запроса не приводят к ошибке.

**Контекстные процессоры** (зарегистрированы в `TEMPLATES`): `stands.context_processors.stand_context` добавляет во все шаблоны `site_name` и `stands_count` (используются в `base.html` и навигации); `bookings.context_processors.booking_status_context` передаёт `BookingStatus` для сравнения статусов в шаблонах.

## 8. Административная панель Django

Адрес: `http://127.0.0.1:8000/admin/`. Для входа нужна учётная запись Django:

```text
python manage.py createsuperuser
```

Названия приложений («Торговые стенды», «Арендаторы», «Бронирования»), моделей и полей русифицированы (`AppConfig.verbose_name`, `verbose_name` моделей и полей, заголовки админки).

| Модель | Настройки `ModelAdmin` |
|--------|------------------------|
| Стенд | столбцы (в том числе «Активных бронирований» – аннотация одним запросом, «Страница на сайте»); поиск по названию; фильтры по типу и признаку «Большой стенд»; сортировка; 20 записей на странице; площадь редактируется прямо в списке (`list_editable`); `id`, `slug`, `is_large` только для чтения; inline-таблица бронирований стенда; ссылка «Смотреть на сайте» (`get_absolute_url()`) |
| Арендатор | столбцы и число бронирований; поиск по имени и email; inline-таблица бронирований арендатора |
| Бронирование | столбцы со стендом, арендатором, площадью; поиск по связанным полям (`stand__name`, `user__name`, `user__email`); фильтры по дате, статусу, стенду; `date_hierarchy`; `list_select_related`; `autocomplete_fields`; действия «Отменить», «Отметить завершёнными», «Вернуть в активные» (с проверкой правила «одна активная бронь на дату») |

Права доступа: стандартные разрешения Django (`view`, `add`, `change`, `delete`) разграничивают действия пользователей. Например, оператор с правами `view_stand`, `add_stand`, `change_stand` без права `delete_stand` не может удалять стенды. Настройки админки **не заменяют бизнес-правила**: конфликт активных бронирований запрещён ограничением модели и проверкой при сохранении формы, а удаление записей с бронированиями – `PROTECT`.

## 9. Django Debug Toolbar

Панель анализа SQL-запросов подключена только для разработки: `debug_toolbar` в `INSTALLED_APPS`, middleware, `INTERNAL_IPS` и маршрут `__debug__/` (только при `DEBUG`). По умолчанию `DEBUG` выключен; для работы с панелью:

```text
$env:DJANGO_DEBUG = "1"     # PowerShell
python manage.py runserver
```

Открыть страницу, в панели справа выбрать раздел SQL. Для статических файлов при `DEBUG = False` используйте `python manage.py runserver --insecure`.

## 10. Структура проекта

```text
проект фреймворк/
├── stands/        # Stand: модель, admin, представления, context_processors, тесты
├── users/         # User (арендатор): модель, admin
├── bookings/      # Booking: статусы, QuerySet/Manager, представления, admin, context_processors
├── homepage/      # главная, страница 404, статические файлы, заголовки админки
├── templates/     # base.html, 404.html, includes/navigation.html
├── fixtures/      # tradestands.json (dumpdata/loaddata)
├── tradestands/   # настройки, urls, sqlite_unicode.py, тесты проекта и админки
├── db/            # скрипты переноса и инспекции данных, модуль SQL-слоя ПР7
├── sql/, data/    # SQL-слой ПР7 и исходная база data/tradestands.sqlite
├── models/, tests/, legacy/   # консольная версия и её тесты
└── main.py, storage.py, utils.py, manage.py
```

Файлы SQL-слоя ПР7 сохранены как предыдущая реализация; веб-представления их не используют. Консольная версия (`main.py`) продолжает работать с JSON.

## 11. Запуск проекта

```text
git clone <адрес репозитория>
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata tradestands.json
python manage.py createsuperuser
python manage.py runserver
```

Открыть `http://127.0.0.1:8000/` (сайт) и `http://127.0.0.1:8000/admin/` (админка). Локальная база `db.sqlite3` в репозиторий не входит. При `DEBUG = False` сервер не раздаёт статику: используйте `runserver --insecure` или `DJANGO_DEBUG=1`.

## 12. Проверка

```text
python manage.py check
python manage.py showmigrations
python manage.py makemigrations --check
python manage.py test        # модели, менеджер, представления, админка, права, миграции
pytest -v                    # консольная версия и SQL-слой ПР7
flake8 . --extend-exclude=venv
```

## 13. Текущее состояние и планы

Реализовано: модели со статусами, менеджер `QuerySet`, `slug` и `get_absolute_url()`, `GeneratedField`, миграции схемы и данных, настроенная админка с inline-формами и правами, контекстные процессоры, оптимизированные запросы, фильтрация, поиск, сортировка, пагинация, статистика, автотесты.

Не реализовано: формы Django для создания и отмены бронирований на сайте, аутентификация арендаторов, API.

## Автор

Манукян Андрей Сержикович, ЭФБО-11-24.
