# Create your views here.

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from rest_framework import serializers, generics, status, permissions, authentication
from rest_framework.response import Response

from data.models import Resource
from quartermaster.allocator import make_reservation, release_reservation, refresh_reservation


class ReservationSerializer(serializers.ModelSerializer):
    reservation_url = serializers.SerializerMethodField()
    devices = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = ['user', 'used_for', 'use_password', 'devices', 'reservation_url']

    def get_reservation_url(self, resource_pk):
        return settings.SERVER_BASE_URL + reverse('api:show_reservation', kwargs={"resource_pk": self.instance.pk})

    def get_devices(self, resource_pk):
        devices = []
        for device in self.instance.device_set.all():
            devices.append({**device.config, 'driver': device.driver, 'name': str(device)})
        return devices


class ReservationView(generics.GenericAPIView):
    queryset = Resource.objects.all()
    serializer_class = ReservationSerializer
    lookup_url_kwarg = 'resource_pk'
    resource: Resource
    permission_classes = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.resource: Resource = self.get_object()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.resource)
        if self.resource.user is None:
            make_reservation(self.resource, user=request.user, used_for=request.data.get('used_for', 'API User'))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif self.resource.user == request.user:
            return Response(serializer.data)
        else:
            return JsonResponse({"message": f"The resource in use by another user, {self.resource.user.username}"},
                                status=403)

    def get(self, request, *args, **kwargs):
        if self.resource.user is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        elif self.resource.user == request.user:
            serializer = self.get_serializer(self.resource)
            return Response(serializer.data)
        else:
            return JsonResponse({"message": f"The resource in use by another user, {self.resource.user.username}"},
                                status=403)

    def delete(self, request, *args, **kwargs):
        release_reservation(self.resource)
        self.resource.refresh_from_db()
        serializer = self.get_serializer(self.resource)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, *args, **kwargs):
        refresh_reservation(resource=self.resource)
        self.resource.refresh_from_db()
        serializer = self.get_serializer(self.resource)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        if self.resource.user == request.user:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ReservationDjangoAuthView(ReservationView):
    pass


class ResourceAuthentication(authentication.BaseAuthentication):
    """
    This allows the use of resources passwords to authenticate.
    On the face this doesn't look great but those passwords will only be presented to authenticated
    users and are rotated when a reservation is complete.
    """

    def authenticate(self, request):
        resource_pk = request.parser_context['kwargs']['resource_pk']
        resource_password = request.parser_context['kwargs']['resource_password']
        resource = Resource.objects.get(pk=resource_pk)

        if resource.user is None:
            return None
        if resource.use_password != resource_password:
            return None

        return (resource.user, None)


class ReservationResourcePasswordView(ReservationView):
    authentication_classes = [ResourceAuthentication]


class ResourceSerializer(serializers.ModelSerializer):

    def __init__(self, *args, platform: str, **kwargs):
        super().__init__(*args, **kwargs)

    resource_url = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = ['used_for', 'last_reserved', 'last_check_in', 'name', 'resource_url']

    def get_resource_url(self, resource_pk):
        return settings.SERVER_BASE_URL + reverse('api:show_resource', kwargs={"resource_pk": self.instance.pk})


class ResourceView(generics.RetrieveAPIView):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    lookup_url_kwarg = 'resource_pk'
