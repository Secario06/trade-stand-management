from django.shortcuts import render


def index(request):
    """Главная страница: описание приложения и навигация."""
    return render(request, "homepage/index.html")


def page_not_found(request, exception):
    """Собственная страница 404 для любого несуществующего адреса."""
    return render(request, "404.html", status=404)
