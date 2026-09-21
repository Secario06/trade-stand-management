from stands import (add_stand, find_stand, filter_stands_by_area,
                    sort_stands_by_area, get_stand_description)
from bookings import (get_booking_status, is_stand_available,
                      create_booking, cancel_booking)
from storage import load_data, save_data
from utils import input_int, input_float, input_date

STANDS_FILE = "data/stands.json"
BOOKINGS_FILE = "data/bookings.json"


def show_stands(stands: dict) -> None:
    """Выводит список всех стендов."""
    if not stands:
        print("Список стендов пуст.")
        return
    print("\n--- Список торговых стендов ---")
    for s_id, s_data in stands.items():
        print(f"ID: {s_id} | Название: {s_data['name']} | "
              f"{get_stand_description(s_data)}")


def show_bookings(bookings: list) -> None:
    """Выводит список всех бронирований."""
    if not bookings:
        print("Список бронирований пуст.")
        return
    print("\n--- Список бронирований ---")
    for b in bookings:
        print(f"ID брони: {b['id']} | ID стенда: {b['stand_id']} | "
              f"Дата: {b['date']}")


def main() -> None:
    """Точка запуска приложения."""
    stands = load_data(STANDS_FILE)
    bookings = load_data(BOOKINGS_FILE)
    if not isinstance(stands, dict):
        stands = {}
    if not isinstance(bookings, list):
        bookings = []

    while True:
        print("\n=== Система управления торговыми стендами ===")
        print("1. Показать все стенды")
        print("2. Добавить стенд")
        print("3. Найти стенд по названию")
        print("4. Фильтр стендов по площади")
        print("5. Проверить доступность стенда на дату")
        print("6. Забронировать стенд")
        print("7. Отменить бронирование")
        print("8. Показать все бронирования")
        print("0. Выход")

        choice = input_int("Выберите действие: ")

        if choice == 1:
            show_stands(stands)
        elif choice == 2:
            name = input("Название стенда: ")
            area = input_float("Площадь (кв.м.): ")
            s_type = input("Тип стенда (Стандарт/Премиум/Остров): ")
            new_id = add_stand(stands, name, area, s_type)
            save_data(STANDS_FILE, stands)
            print(f"Стенд добавлен с ID {new_id}.")
        elif choice == 3:
            query = input("Введите часть названия для поиска: ")
            results = find_stand(stands, query)
            if results:
                print(f"Найдено стендов: {len(results)}")
                for s_id, s_data in results.items():
                    print(f"ID: {s_id} | {s_data['name']} | "
                          f"Площадь: {s_data['area']}")
            else:
                print("Ничего не найдено.")
        elif choice == 4:
            min_area = input_float("Минимальная площадь: ")
            filtered = filter_stands_by_area(stands, min_area)
            if filtered:
                sorted_filtered = sort_stands_by_area(filtered)
                print("\n--- Отфильтрованные и "
                      "отсортированные стенды ---")
                for s_id, s_data in sorted_filtered.items():
                    print(f"ID: {s_id} | {s_data['name']} | "
                          f"Площадь: {s_data['area']}")
            else:
                print("Нет стендов с такой площадью.")
        elif choice == 5:
            stand_id = input_int("ID стенда: ")
            date_str = input_date("Дата (ДД.ММ.ГГГГ): ")
            available = is_stand_available(bookings, stand_id, date_str)
            print(get_booking_status(available))
        elif choice == 6:
            stand_id = input_int("ID стенда: ")
            date_str = input_date("Дата (ДД.ММ.ГГГГ): ")
            result = create_booking(bookings, stand_id, date_str)
            if result:
                save_data(BOOKINGS_FILE, bookings)
                print(f"Бронирование создано (ID: {result['id']}).")
            else:
                print("Ошибка: стенд уже занят на эту дату.")
        elif choice == 7:
            booking_id = input_int("ID бронирования для отмены: ")
            if cancel_booking(bookings, booking_id):
                save_data(BOOKINGS_FILE, bookings)
                print("Бронирование отменено.")
            else:
                print("Бронирование с таким ID не найдено.")
        elif choice == 8:
            show_bookings(bookings)
        elif choice == 0:
            print("Выход из программы.")
            break
        else:
            print("Неверный пункт меню. Попробуйте снова.")


if __name__ == "__main__":
    main()
