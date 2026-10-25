# Система управления торговыми стендами

Система учёта торговых стендов и их бронирования на Python с веб-интерфейсом на Django и базой данных SQLite.

## 1. Назначение проекта

Приложение для управления торговыми стендами и их бронированием. Проект позволяет хранить сведения о стендах, арендаторах и бронированиях, выполнять основные операции с этими объектами и просматривать информацию через веб-интерфейс Django.

Проект развивается поэтапно: консольная версия (ПР3) дополнена веб-интерфейсом (ПР5), он переведён на шаблоны Django (ПР6), а данные перенесены из JSON в реляционную базу SQLite (ПР7).

## 2. Используемые технологии

- Python 3;
- Django 5.2;
- Django Template Language (DTL);
- SQLite и стандартная библиотека `sqlite3` (SQL без Django ORM);
- HTML5, CSS3, JavaScript;
- Bootstrap 5.3 (через CDN);
- JSON (исходные данные и консольная версия);
- Git;
- pytest;
- flake8.

## 3. Предметная область

В системе используются три основные сущности:

- Стенд (`Stand`) – идентификатор, название, площадь, тип;
- Арендатор (`User`) – идентификатор, имя и email;
- Бронирование (`Booking`) – идентификатор, стенд, арендатор, дата бронирования и признак отмены.

Для предметной области реализованы собственные Python-классы (пакет `models/`). Один стенд не может иметь два активных бронирования на одну дату; отменённое бронирование стенд не блокирует.

## 4. Структура проекта

```text
проект фреймворк/
├── bookings/               # приложение: бронирования и статистика
│   ├── templates/bookings/ # booking_list, booking_detail, statistics,
│   │                       # includes/booking_status
│   ├── urls.py, views.py, tests.py
├── homepage/               # приложение: главная, страница 404, static
│   ├── static/homepage/    # css/style.css, js/main.js, img/logo.png
│   ├── templates/homepage/index.html
│   ├── urls.py, views.py, tests.py
├── stands/                 # приложение: стенды и поиск свободных
│   ├── templates/stands/   # stand_list, stand_detail, available,
│   │                       # includes/stand_card
│   ├── urls.py, views.py, tests.py
├── templates/              # base.html, 404.html, includes/navigation.html
│
├── db/                     # слой базы данных (ПР7)
│   ├── database.py         # подключение к SQLite
│   └── import_json.py      # перенос данных из JSON в SQLite
├── sql/
│   ├── schema.sql          # создание таблиц
│   └── queries.sql         # SQL-запросы проекта
├── data/
│   ├── tradestands.sqlite  # база данных SQLite
│   └── stands.json, users.json, bookings.json   # исходные данные
│
├── models/                 # классы предметной области (ПР3)
├── tests/                  # pytest-тесты (предметная область, БД)
├── tradestands/            # конфигурация Django-проекта
├── legacy/                 # модули ПР2 (не используются)
├── main.py, storage.py, utils.py   # консольная версия (JSON)
├── manage.py
└── README.md
```

Отдельное приложение для пользователей не создаётся: Django предоставляет встроенную модель `User`.

## 5. База данных (ПР7)

База данных `data/tradestands.sqlite` – один файл SQLite. Структура задана в `sql/schema.sql` (повторный запуск безопасен: `CREATE TABLE IF NOT EXISTS`).

### Таблица `stands` – торговые стенды

| Поле | Тип | Назначение |
|------|-----|------------|
| `id` | INTEGER, PRIMARY KEY | идентификатор |
| `name` | TEXT, NOT NULL | название стенда |
| `area` | REAL, NOT NULL, `CHECK (area > 0)` | площадь, кв.м |
| `stand_type` | TEXT, NOT NULL | тип (Стандарт, Премиум, Остров) |

### Таблица `users` – арендаторы

| Поле | Тип | Назначение |
|------|-----|------------|
| `id` | INTEGER, PRIMARY KEY | идентификатор |
| `name` | TEXT, NOT NULL | имя или название организации |
| `email` | TEXT, NOT NULL | электронная почта |

### Таблица `bookings` – бронирования

| Поле | Тип | Назначение |
|------|-----|------------|
| `id` | INTEGER, PRIMARY KEY | идентификатор |
| `stand_id` | INTEGER, NOT NULL, FOREIGN KEY → `stands(id)` | стенд |
| `user_id` | INTEGER, NOT NULL, FOREIGN KEY → `users(id)` | арендатор |
| `booking_date` | TEXT, NOT NULL | дата в формате `ГГГГ-ММ-ДД` |
| `is_cancelled` | INTEGER, NOT NULL, DEFAULT 0 | 0 – активно, 1 – отменено |

Связи: один стенд и один арендатор могут иметь много бронирований; каждое бронирование относится к одному стенду и одному арендатору. Дополнительно: индекс по `(stand_id, booking_date)` и уникальный индекс, запрещающий два **активных** бронирования стенда на одну дату.

### Подключение и импорт

- `db/database.py` – `get_connection()` включает `PRAGMA foreign_keys = ON`; `open_connection()` для веб-представлений настраивает `sqlite3.Row` (доступ к полям по именам) и закрывает соединение. Если файла базы нет, возникает понятная ошибка, а не пустая база.
- `db/import_json.py` – создаёт таблицы и переносит данные из JSON (порядок: стенды, арендаторы, бронирования). Повторный запуск не затирает данные; для перезаполнения нужен флаг `--reset`.

### SQL-запросы

В `sql/queries.sql` сохранено 20 проверенных запросов: списки (`SELECT`, `DISTINCT`), фильтрация (`WHERE`, `BETWEEN`, `LIKE`), соединения (`JOIN`), подзапрос `NOT IN` (свободные стенды), агрегаты (`COUNT`, `MIN`, `MAX`, `AVG`, `SUM`), группировка (`GROUP BY`), фильтрация групп (`HAVING`), сортировка и `LIMIT/OFFSET`. Значения в веб-приложении передаются параметрами `?`, подстановка через f-строки не используется.

## 6. Веб-интерфейс

| URL | Имя маршрута | Данные (SQL) |
|-----|--------------|--------------|
| `/` | `homepage:index` | – |
| `/stands/` | `stands:list` | список стендов; поиск `?q=`, фильтр `?min_area=` (`WHERE`, параметры) |
| `/stands/<id>/` | `stands:detail` | стенд, занятость на дату `?date=` (`COUNT`), история бронирований (`JOIN`) |
| `/stands/available/` | `stands:available` | стенды, свободные на дату `?date=` (подзапрос `NOT IN`) |
| `/bookings/` | `bookings:bookings` | активные бронирования (`JOIN`); `?show=all` – вместе с отменёнными |
| `/bookings/<id>/` | `bookings:detail` | бронирование с данными стенда и арендатора (`JOIN`) |
| `/bookings/statistics/` | `bookings:statistics` | агрегаты, `GROUP BY`, `HAVING`, `LIMIT` |

Представления выполняют SQL-запрос, получают строки `sqlite3.Row`, передают их в шаблон через контекст; страница создаётся шаблоном Django. Если объект не найден, возвращается страница с кодом 404; для несуществующих адресов подключён `handler404`.

## 7. Django Template Language

- базовый шаблон `templates/base.html` с блоками `title` и `content`, дочерние шаблоны используют `{% extends %}`;
- включаемые шаблоны: навигация, карточка стенда, статус бронирования;
- данные передаются через контекст, используются `{% for %}` с `{% empty %}` и `{% if %}`;
- фильтры: `length`, `default`, `floatformat`, `date`;
- ссылки формируются через `{% url %}` с пространствами имён (`stands:`, `bookings:`, `homepage:`);
- статика (`homepage/static/homepage/`): собственные CSS, JavaScript и логотип подключаются через `{% load static %}`.

## 8. Хранение данных

- Веб-приложение работает с базой SQLite `data/tradestands.sqlite`.
- JSON-файлы `data/stands.json`, `data/users.json`, `data/bookings.json` сохранены: они служат источником данных для импорта и используются консольной версией (`main.py`, `storage.py`).
- Django ORM и модели Django на текущем этапе не используются; формы не реализованы.

## 9. Тестирование и качество кода

```text
python manage.py check
python manage.py test        # веб-страницы (на временной копии БД)
pytest -v                    # предметная область, БД, файл queries.sql
flake8 . --extend-exclude=venv
```

Веб-тесты создают временную базу из JSON и не изменяют рабочий файл `tradestands.sqlite`.

## 10. Запуск проекта

```text
pip install -r requirements.txt
python -m db.import_json     # создать и заполнить базу (если файла нет)
python manage.py migrate
python manage.py runserver
```

После запуска открыть `http://127.0.0.1:8000/`. Консольная версия: `python main.py`.

Пересоздать базу из JSON: `python -m db.import_json --reset`. При `DEBUG = False` сервер разработки не раздаёт статику: для просмотра с оформлением используйте `python manage.py runserver --insecure` или включите `DEBUG = True`.

## 11. Текущее состояние проекта

Реализовано:

- предметные классы, консольный интерфейс (JSON), тесты;
- Django-проект `tradestands`, приложения `homepage`, `stands`, `bookings`;
- шаблоны Django, наследование, `include`, фильтры, именованные URL, статика;
- база данных SQLite: схема, ключи, импорт из JSON, 20 SQL-запросов;
- веб-страницы, получающие данные из SQLite: список и страница стенда, активные бронирования, поиск свободных стендов на дату, статистика.

Формы Django, модели Django ORM и миграции для данных проекта пока не реализованы.

## 12. Дальнейшее развитие

Подключение базы данных к Django через ORM и миграции, формы создания и отмены бронирований, добавления стендов, аутентификация, API.
