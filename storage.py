import json
import os


def load_data(filename: str) -> dict | list:
    """Загружает данные из JSON-файла."""
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"Ошибка: файл {filename} поврежден.")
        return {}
    except Exception as e:
        print(f"Непредвиденная ошибка при чтении {filename}: {e}")
        return {}


def save_data(filename: str, data: dict | list) -> None:
    """Сохраняет данные в JSON-файл."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка при сохранении в {filename}: {e}")
