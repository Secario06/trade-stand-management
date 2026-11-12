"""Регистрация Unicode-aware функции like() для соединений SQLite.

Встроенный оператор LIKE в SQLite не учитывает регистр только для
ASCII-символов, поэтому фильтр icontains не находил бы «павильон» в
названии «Павильон А». SQLite допускает переопределение функции like(),
на которую опирается оператор LIKE: здесь она заменяется версией на
Python, сравнивающей строки без учёта регистра для любых символов.
"""
import re


def _like(pattern, value, escape=None):
    """Реализация SQL LIKE: % – любая подстрока, _ – один символ."""
    if pattern is None or value is None:
        return None
    pattern, value = str(pattern), str(value)

    regex = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if escape and char == escape and i + 1 < len(pattern):
            i += 1
            regex.append(re.escape(pattern[i]))
        elif char == "%":
            regex.append(".*")
        elif char == "_":
            regex.append(".")
        else:
            regex.append(re.escape(char))
        i += 1

    found = re.fullmatch(
        "".join(regex),
        value,
        re.IGNORECASE | re.DOTALL,
    )
    return 1 if found else 0


def register_like(sender, connection, **kwargs):
    """Обработчик сигнала connection_created."""
    if connection.vendor != "sqlite":
        return
    raw = connection.connection
    raw.create_function("like", 2, _like, deterministic=True)
    raw.create_function("like", 3, _like, deterministic=True)
