import io
import zipapp

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(("GET",))
def download_client(request):
    # TODO 
    #  #open new driver/__init__.py
    # 
    # for driver in settings.drivers_to_add:
    #     # Find driver path
    #     # Copy client.py to Driver.py
    #     # Write 
    quartermaster_client = io.BytesIO()
    zipapp.create_archive('client/quartermaster_client', quartermaster_client, '/usr/bin/env python3')
    response = HttpResponse(quartermaster_client.getvalue(), content_type='application/python')
    response['Content-Disposition'] = 'attachment; filename="quartermaster_client"'
    return response
