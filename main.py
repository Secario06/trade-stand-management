from datetime import date


student_name = "Манукян Андрей Сержикович"
student_group = "ЭФБО-11-24"
project_name = "Система управления торговыми стендами"

fair_name = "Осенняя городская ярмарка"
fair_date = date(2026, 9, 20)
is_fair_active = True

stand_number = "A-12"
stand_area = 12.5
stand_has_electricity = True
stand_is_available = True
base_price_per_meter = 900
electricity_price = 1500

seller_name = "Кофейная лавка"
seller_has_documents = True
seller_rating = 4.7
minimum_rating = 4.0

booking_days_text = "3"
booking_days = int(booking_days_text)
booking_date = date.today()

area_price = stand_area * base_price_per_meter
electricity_total = electricity_price if stand_has_electricity else 0
day_price = area_price + electricity_total
total_price = day_price * booking_days

print(project_name)
print(f"Студент: {student_name}")
print(f"Группа: {student_group}")
print()
print(f"Ярмарка: {fair_name}")
print(f"Дата ярмарки: {fair_date}")
print(f"Стенд: {stand_number}")
print(f"Площадь стенда: {stand_area} кв. м")
print(f"Продавец: {seller_name}")
print(f"Дата проверки бронирования: {booking_date}")
print()

if not is_fair_active:
    print("Бронирование невозможно: ярмарка не активна.")
elif not stand_is_available:
    print("Бронирование невозможно: стенд уже занят.")
elif not seller_has_documents:
    print("Бронирование невозможно: у продавца не проверены документы.")
elif seller_rating < minimum_rating:
    print("Бронирование невозможно: рейтинг продавца ниже минимального.")
else:
    print("Бронирование возможно.")
    print(f"Стоимость за один день: {day_price:.2f} руб.")
    print(f"Количество дней: {booking_days}")
    print(f"Итоговая стоимость: {total_price:.2f} руб.")

if stand_has_electricity:
    print("Стенд подключен к электричеству.")
else:
    print("Стенд без подключения к электричеству.")
