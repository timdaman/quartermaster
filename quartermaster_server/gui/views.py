import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect, HttpResponseNotFound
# Create your views here.
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from data.models import Resource
from quartermaster.allocator import release_reservation, make_reservation, update_reservation

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(("GET",))
@never_cache
def list_resources(request):
    resource_qs = Resource.everything.all()
    return TemplateResponse(request=request,
                            template='resource_list.html',
                            context={"resources": resource_qs})


def get_resource(func):
    """
    Decorator ensure the requested resource exists and supplies it to the wrapped methods
    """

    def wrapper(request, *args, **kwargs):
        resource_pk = kwargs['resource_pk']
        try:
            resource = Resource.objects.get(pk=resource_pk)
        except Resource.DoesNotExist:
            messages.error(request, f"No resource found matching '{resource_pk}'")
            response = HttpResponseNotFound()
            logger.warning(f"Resource not found '{resource_pk}' {request.method} {request.path}")
            return HttpResponseRedirect(reverse('gui:list_resources'))
        return func(request, resource, *args, **kwargs)

    return wrapper


@method_decorator(get_resource, name='dispatch')
@method_decorator(login_required, name='dispatch')
class ReservationView(View):

    def reservation_active_response(self, resource) -> TemplateResponse:
        update_reservation(resource)

        return TemplateResponse(request=self.request,
                                template='resource_detail.html',
                                context={"resource": resource})

    def post(self, request, resource, *args, **kwargs):
        if 'DELETE' in request.POST:
            return self.delete(request, resource)

        if resource.in_use:
            return HttpResponseForbidden("The resource is already in use")

        make_reservation(resource, request.user, used_for="GUI")
        return HttpResponseRedirect(reverse('gui:view_reservation', kwargs={'resource_pk': resource.pk}))

    def get(self, request, resource, *args, **kwargs):
        if request.user == resource.user:
            return self.reservation_active_response(resource)
        elif resource.user is None:
            messages.error(request, f"No active reservation for {resource.pk}, perhaps yours expired?")
        else:
            messages.error(request, f"The resource, {resource.pk},  is already in use by another user or service")
        return HttpResponseRedirect(reverse('gui:list_resources'))

    def delete(self, request, resource, *args, **kwargs):
        if request.user == resource.user:
            release_reservation(resource)
            return HttpResponseRedirect(reverse('gui:list_resources'))
        messages.error(request, f"The resource, {resource.pk},  was not released because it is not reserved by you")
        return HttpResponseRedirect(reverse('gui:list_resources'))
