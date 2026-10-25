-- ==========================================
-- Торговые стенды: структура базы данных
-- ==========================================

-- Торговые стенды
CREATE TABLE IF NOT EXISTS stands (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    area REAL NOT NULL CHECK (area > 0),
    stand_type TEXT NOT NULL
);

-- Арендаторы
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

-- Бронирования: каждое относится к одному стенду и одному арендатору
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY,
    stand_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    is_cancelled INTEGER NOT NULL DEFAULT 0
        CHECK (is_cancelled IN (0, 1)),
    FOREIGN KEY (stand_id) REFERENCES stands(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Ускорение поиска бронирований по стенду и дате
CREATE INDEX IF NOT EXISTS idx_bookings_stand_date
    ON bookings(stand_id, booking_date);

-- Правило предметной области: на одну дату у стенда
-- не может быть двух активных бронирований
CREATE UNIQUE INDEX IF NOT EXISTS ux_bookings_active_stand_date
    ON bookings(stand_id, booking_date)
    WHERE is_cancelled = 0;
