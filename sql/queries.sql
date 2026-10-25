-- ==========================================================
-- Торговые стенды: SQL-запросы проекта
--
-- Запросы проверены в SQLite. Значения в запросах (30, '2026-10-15'
-- и т.п.) приведены для проверки: в веб-приложении они передаются
-- параметрами ? (см. stands/views.py и bookings/views.py).
-- ==========================================================


-- ----------------------------------------------------------
-- ВЫБОРКА СПИСКОВ
-- ----------------------------------------------------------

-- 1. Список всех стендов (страница /stands/)
SELECT
    id,
    name,
    area,
    stand_type
FROM stands
ORDER BY name;

-- 2. Список арендаторов
SELECT
    id,
    name,
    email
FROM users
ORDER BY name;

-- 3. Типы стендов без повторов (DISTINCT)
SELECT DISTINCT
    stand_type
FROM stands
ORDER BY stand_type;


-- ----------------------------------------------------------
-- ФИЛЬТРАЦИЯ (WHERE)
-- ----------------------------------------------------------

-- 4. Стенды площадью не менее 25 кв.м (фильтр на /stands/?min_area=)
SELECT
    id,
    name,
    area,
    stand_type
FROM stands
WHERE area >= 25
ORDER BY area;

-- 5. Поиск по названию и площади одновременно (/stands/?q=&min_area=)
--    Примечание: LIKE в SQLite учитывает регистр кириллицы, поэтому
--    в приложении используется lower(name) LIKE lower(?).
SELECT
    id,
    name,
    area,
    stand_type
FROM stands
WHERE name LIKE '%Павильон%'
  AND area BETWEEN 10 AND 30
ORDER BY name;

-- 6. Активные (не отменённые) бронирования
SELECT
    id,
    stand_id,
    user_id,
    booking_date
FROM bookings
WHERE is_cancelled = 0
ORDER BY booking_date;

-- 7. Отменённые бронирования или бронирования на заданный период
SELECT
    id,
    stand_id,
    booking_date,
    is_cancelled
FROM bookings
WHERE is_cancelled = 1
   OR booking_date BETWEEN '2026-10-20' AND '2026-10-31'
ORDER BY booking_date;


-- ----------------------------------------------------------
-- СОЕДИНЕНИЕ ТАБЛИЦ (JOIN)
-- ----------------------------------------------------------

-- 8. Активные бронирования с названием стенда и именем арендатора
--    (страница /bookings/)
SELECT
    bookings.id,
    bookings.booking_date,
    stands.name AS stand_name,
    stands.area,
    users.name AS user_name,
    users.email
FROM bookings
JOIN stands
    ON bookings.stand_id = stands.id
JOIN users
    ON bookings.user_id = users.id
WHERE bookings.is_cancelled = 0
ORDER BY bookings.booking_date;

-- 9. Полная информация об одном бронировании
--    (страница /bookings/<id>/, id передаётся параметром)
SELECT
    bookings.id,
    bookings.booking_date,
    bookings.is_cancelled,
    stands.id AS stand_id,
    stands.name AS stand_name,
    users.name AS user_name,
    users.email
FROM bookings
JOIN stands
    ON bookings.stand_id = stands.id
JOIN users
    ON bookings.user_id = users.id
WHERE bookings.id = 1;

-- 10. История бронирований одного стенда (страница /stands/<id>/)
SELECT
    bookings.id,
    bookings.booking_date,
    bookings.is_cancelled,
    users.name AS user_name
FROM bookings
JOIN users
    ON bookings.user_id = users.id
WHERE bookings.stand_id = 1
ORDER BY bookings.booking_date;

-- 11. Три последних бронирования (ORDER BY + LIMIT)
SELECT
    bookings.id,
    bookings.booking_date,
    stands.name AS stand_name,
    users.name AS user_name
FROM bookings
JOIN stands
    ON bookings.stand_id = stands.id
JOIN users
    ON bookings.user_id = users.id
ORDER BY bookings.id DESC
LIMIT 3;

-- 12. Постраничный вывод стендов: вторая страница по 2 записи
--     (LIMIT и OFFSET всегда используются вместе с ORDER BY)
SELECT
    id,
    name
FROM stands
ORDER BY name
LIMIT 2 OFFSET 2;


-- ----------------------------------------------------------
-- ПОДЗАПРОС: СВОБОДНЫЕ СТЕНДЫ НА ДАТУ
-- ----------------------------------------------------------

-- 13. Стенды без активного бронирования на выбранную дату
--     (страница /stands/available/?date=)
SELECT
    stands.id,
    stands.name,
    stands.area,
    stands.stand_type
FROM stands
WHERE stands.id NOT IN (
    SELECT bookings.stand_id
    FROM bookings
    WHERE bookings.booking_date = '2026-10-15'
      AND bookings.is_cancelled = 0
)
ORDER BY stands.name;


-- ----------------------------------------------------------
-- АГРЕГАТНЫЕ ФУНКЦИИ
-- ----------------------------------------------------------

-- 14. Количество активных бронирований
SELECT
    COUNT(*) AS bookings_count
FROM bookings
WHERE is_cancelled = 0;

-- 15. Занят ли стенд на дату: 0 – свободен, 1 – занят
--     (блок «Доступность» на странице стенда)
SELECT
    COUNT(*) AS busy
FROM bookings
WHERE stand_id = 1
  AND booking_date = '2026-10-15'
  AND is_cancelled = 0;

-- 16. Сводка по площади стендов: количество, минимум, максимум,
--     среднее и сумма
SELECT
    COUNT(*) AS stands_count,
    MIN(area) AS min_area,
    MAX(area) AS max_area,
    AVG(area) AS avg_area,
    SUM(area) AS total_area
FROM stands;


-- ----------------------------------------------------------
-- ГРУППИРОВКА (GROUP BY) И ФИЛЬТРАЦИЯ ГРУПП (HAVING)
-- ----------------------------------------------------------

-- 17. Количество активных бронирований каждого стенда
--     (включая стенды без бронирований; страница /bookings/statistics/)
SELECT
    stands.name AS stand_name,
    COUNT(bookings.id) AS bookings_count
FROM stands
LEFT JOIN bookings
    ON stands.id = bookings.stand_id
   AND bookings.is_cancelled = 0
GROUP BY stands.id, stands.name
ORDER BY bookings_count DESC, stands.name;

-- 18. Количество активных бронирований каждого арендатора
SELECT
    users.name AS user_name,
    COUNT(bookings.id) AS bookings_count
FROM users
LEFT JOIN bookings
    ON users.id = bookings.user_id
   AND bookings.is_cancelled = 0
GROUP BY users.id, users.name
ORDER BY bookings_count DESC, users.name;

-- 19. Количество стендов и средняя площадь по типам стендов
SELECT
    stand_type,
    COUNT(*) AS stands_count,
    AVG(area) AS avg_area
FROM stands
GROUP BY stand_type
ORDER BY stand_type;

-- 20. Востребованные стенды: более одного активного бронирования
--     (HAVING фильтрует группы, WHERE – отдельные записи)
SELECT
    stands.name AS stand_name,
    COUNT(bookings.id) AS bookings_count
FROM stands
JOIN bookings
    ON stands.id = bookings.stand_id
WHERE bookings.is_cancelled = 0
GROUP BY stands.id, stands.name
HAVING COUNT(bookings.id) > 1
ORDER BY bookings_count DESC, stands.name;
