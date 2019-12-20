from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
# Create your views here.
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from data.models import Resource
from quartermaster.allocator import release_reservation, make_reservation, update_reservation
from quartermaster.helpers import for_all_devices


@login_required
@require_http_methods(("GET",))
@never_cache
def list_resources(request):
    resource_qs = Resource.everything.all()
    return TemplateResponse(request=request,
                            template='resource_list.html',
                            context={"resources": resource_qs,
                                     "server_base_url": settings.SERVER_BASE_URL})


@method_decorator(login_required, name='dispatch')
class ReservationView(View):
    resource: Optional[Resource] = None

    def setup(self, request, *args, **kwargs):
        self.resource = Resource.objects.get(pk=kwargs['resource_pk'])
        super().setup(request, *args, **kwargs)

    def reservation_active_response(self) -> TemplateResponse:
        update_reservation(self.resource)
        instructions = {platform: {'setup': set(), 'attach': []}
                        for platform in settings.SUPPORTED_PLATFORMS}

        return TemplateResponse(request=self.request,
                                template='reserve_resource.html',
                                context={"resource": self.resource,
                                         "server_base_url": settings.SERVER_BASE_URL})

    def post(self, request, resource_pk: str):
        if 'DELETE' in request.POST:
            return self.delete(request, resource_pk)

        if self.resource.in_use:
            return HttpResponseForbidden("The resource is already in use")

        make_reservation(self.resource, request.user, used_for="GUI")
        return HttpResponseRedirect(reverse('gui:view_reservation', kwargs={'resource_pk': resource_pk}))

    def get(self, request, resource_pk: str):
        if request.user == self.resource.user:
            return self.reservation_active_response()
        elif self.resource.user is None:
            messages.error(request, f"No active reservation for {resource_pk}, perhaps yours expired?")
        else:
            messages.error(request, f"The resource, {resource_pk},  is already in use by another user or service")
        return HttpResponseRedirect(reverse('gui:list_resources'))

    def delete(self, request, resource_pk: str):
        if request.user == self.resource.user:
            release_reservation(self.resource)
            for_all_devices(self.resource.device_set.all(), 'unshare')
            return HttpResponseRedirect(reverse('gui:list_resources'))
        messages.error(request, f"The resource, {resource_pk},  was not released because it is not reserved by you")
        return HttpResponseRedirect(reverse('gui:list_resources'))
