from stands.models import Stand


def stand_context(request):
    """Передаёт общие данные в шаблоны проекта.

    Возвращаемый словарь добавляется в контекст каждого шаблона:
    название сайта и актуальное число стендов (для навигации).
    """
    return {
        "site_name": "Торговые стенды",
        "stands_count": Stand.objects.count(),
    }
