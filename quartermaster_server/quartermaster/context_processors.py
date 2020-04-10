from django.conf import settings


def add_server_base_url(request):
    return {'server_base_url': settings.SERVER_BASE_URL}
