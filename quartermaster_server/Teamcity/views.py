# Create your views here.
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from Teamcity.tc_allocator import teamcity_release_reservation
from data.models import Resource


@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def build_reservation(request, build_id: int):
    try:
        used_for = f"Teamcity_ID={build_id}"
        resource = Resource.objects.get(used_for=used_for)
        if request.method == "DELETE":
            teamcity_release_reservation(resource=resource)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return HttpResponseRedirect(reverse('api:show_reservation', kwargs={'resource_pk': resource.pk}))
    except Resource.DoesNotExist as e:
        return HttpResponseNotFound("That resource reservation for that build was not found")
