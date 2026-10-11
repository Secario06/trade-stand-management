from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape


def page(title, content):
    """Собрать HTML-документ: кодировка, Bootstrap 5.3 и навигация."""
    bootstrap = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3"
        "/dist/css/bootstrap.min.css"
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="{bootstrap}">
</head>
<body>
    <nav class="navbar navbar-expand navbar-dark bg-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="{reverse("index")}">
                Торговые стенды
            </a>
            <div class="navbar-nav">
                <a class="nav-link" href="{reverse("index")}">Главная</a>
                <a class="nav-link" href="{reverse("stands")}">Стенды</a>
                <a class="nav-link" href="{reverse("bookings")}">
                    Бронирования
                </a>
            </div>
        </div>
    </nav>
    <main class="container">{content}</main>
</body>
</html>"""


def index(request):
    """Главная страница: описание приложения и навигация."""
    content = f"""
    <h1 class="display-4">Система управления торговыми стендами</h1>
    <p class="lead">Учёт стендов и управление их бронированием.</p>
    <p>Основные разделы:</p>
    <a href="{reverse("stands")}" class="btn btn-primary me-2">Стенды</a>
    <a href="{reverse("bookings")}" class="btn btn-secondary">
        Бронирования
    </a>
    """
    return HttpResponse(page("Торговые стенды", content))


def page_not_found(request, exception):
    """Собственная страница 404 для любого несуществующего адреса."""
    content = f"""
    <h1 class="text-danger">404 – страница не найдена</h1>
    <p>Проверьте адрес или вернитесь на главную.</p>
    <a href="{reverse("index")}" class="btn btn-primary">На главную</a>
    """
    return HttpResponse(
        page("404 – страница не найдена", content),
        status=404,
    )
