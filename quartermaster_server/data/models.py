import json
from datetime import datetime
from typing import List, Type, Tuple

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
# Create your models here.
from django.db.models import Q, Count
from django.forms import Textarea
from django.utils.functional import lazy

from USB_Quartermaster_common import AbstractShareableDeviceDriver, AbstractCommunicator, plugins
from quartermaster.helpers import get_driver_obj, get_communicator_obj, get_communicator_class


class ConfigJSON(object):

    @property
    def config(self):
        return json.loads(self.config_json, strict=False)  # strict=False is there to allow use of \n in json values

    def set_config(self, config: dict):
        self.config_json = json.dumps(config)

    def validate_configuration_json(self, keys: List[str]) -> List[str]:
        # TODO: Handle nested keys
        errors_found = []
        try:
            data = json.loads(self.config_json, strict=False)
            data_keys = set(data.keys())
            required_keys = set(keys)
            missing_keys = required_keys - data_keys
            for key in missing_keys:
                errors_found.append(f"Value for '{key}' is needed")
        except json.JSONDecodeError as e:
            errors_found.append(f"Invalid json, {repr(e)}")
        return errors_found


class Pool(models.Model):
    """
    A pool is a collection fo resources that a reasonably similar
    """

    name = models.SlugField(blank=False, null=False, primary_key=True)

    def __str__(self):
        return self.name


class ResourceHideDisabledOfflineManager(models.Manager):
    def get_queryset(self):
        offline_devices = Count('device', filter=Q(device__online=False))
        return super().get_queryset().annotate(offline_devices=offline_devices).filter(enabled=True, offline_devices=0)


class Resource(models.Model):
    """
    A resource is logical collection of usb devices which are treated as a single unit.
    This is the thing a user looks for to attach to their host
    """
    UNUSED = [None, ""]

    pool = models.ForeignKey(Pool, blank=False, null=False, on_delete=models.CASCADE)
    name = models.SlugField(blank=False, null=False, primary_key=True)
    description = models.TextField()
    last_check_in = models.DateTimeField(null=True, blank=True)
    last_reserved = models.DateTimeField(null=True, blank=True)
    # Make this required for reservations
    used_for = models.CharField(null=True, blank=True, max_length=30)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.DO_NOTHING)
    # Make this required for reservations
    use_password = models.CharField(null=True, blank=True, max_length=30,
                                    help_text="Random password needed to request access to devices in this resource")
    enabled = models.BooleanField(default=True)

    # Everything in DB
    everything = models.Manager()

    # By default ignore disabled
    objects = ResourceHideDisabledOfflineManager()

    def __str__(self):
        return f"{str(self.pool)} / {self.name}"

    @property
    def in_use(self) -> bool:
        return self.user is not None

    @property
    def is_online(self) -> bool:
        return self.device_set.filter(online=False).count() == 0

    # This is the time when the reservation expires when in_use() is True
    @property
    def reservation_expiration(self) -> datetime:
        return self.last_reserved + settings.RESERVATION_MAX_MINUTES

    # This is the time when the reservation expires due ot missing check-ins when in_use() is True
    @property
    def checkin_expiration(self) -> datetime:
        return self.last_check_in + settings.RESERVATION_CHECKIN_TIMEOUT_MINUTES


def device_driver_choices() -> List[Tuple[str, str]]:
    driver_classes = plugins.shareable_device_classes()
    return sorted(list((driver.IDENTIFIER, driver.IDENTIFIER) for driver in driver_classes))


def device_host_choices() -> List[Tuple[str, str]]:
    driver_classes = plugins.remote_host_classes()
    return sorted(list((driver.IDENTIFIER, driver.IDENTIFIER) for driver in driver_classes))


def communicator_choices() -> List[Tuple[str, str]]:
    communicator_classes = plugins.communicator_classes()
    return sorted(list((driver.IDENTIFIER, driver.IDENTIFIER) for driver in communicator_classes))


class RemoteHost(models.Model, ConfigJSON):
    # Keep this list sorted to reduce how many DB migrations are generated
    SUPPORTED_HOST_TYPES = sorted(("Darwin", "Linux_AMD64", "Windows"))

    address = models.CharField(max_length=256, null=False, blank=False)
    communicator = models.CharField(max_length=50, null=False, blank=False,
                                    choices=lazy(communicator_choices, list)())
    config_json = models.TextField()
    type = models.CharField(max_length=20, null=False, blank=False,
                            choices=((sht, sht) for sht in SUPPORTED_HOST_TYPES))

    def get_communicator_obj(self) -> AbstractCommunicator:
        return get_communicator_obj(self)

    def get_communicator_class(self) -> Type[AbstractCommunicator]:
        return get_communicator_class(self.communicator)

    def clean(self):
        # Check valid driver is used
        communicator_class = self.get_communicator_class()
        errors = self.validate_configuration_json(communicator_class.CONFIGURATION_KEYS)
        errors_message = ', '.join(errors)
        if errors:
            raise ValidationError({'config_json': errors_message})

    def __str__(self):
        return f"{self.communicator}:{str(self.address)}"


class DeviceHideOfflineManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(online=True)


class Device(models.Model, ConfigJSON):
    """
    Device represents a single USB resource that is being made available from a remote host
    """

    class Meta:
        unique_together = [['name', 'resource']]

    id = models.AutoField(primary_key=True)  # Prep for moving primary key
    resource = models.ForeignKey(Resource, blank=False, null=True, on_delete=models.CASCADE)

    # Choices for `driver` are set dynamically set when the admin form is displayed. This is because
    # when the model is loaded not all the apps are online so we can yet probe for installed plugins
    driver = models.CharField(blank=False, null=False, max_length=100,
                              choices=lazy(device_driver_choices, list)())
    host = models.ForeignKey(RemoteHost, on_delete=models.DO_NOTHING, blank=False, null=False)
    config_json = models.TextField()
    name = models.SlugField(blank=False, null=False, max_length=30)
    online = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{str(self.resource)} / {self.name}@{self.host}"

    everything = models.Manager()

    objects = DeviceHideOfflineManager()

    @property
    def in_use(self) -> bool:
        return self.resource.in_use

    def get_driver(self) -> AbstractShareableDeviceDriver:
        return get_driver_obj(self)

    def clean(self):
        # Check valid driver is used
        shareable_device_driver: AbstractShareableDeviceDriver = self.get_driver()
        errors = self.validate_configuration_json(shareable_device_driver.CONFIGURATION_KEYS)

        # Confirm driver is compatible with communicator on host
        if self.host.communicator not in shareable_device_driver.host_driver.SUPPORTED_COMMUNICATORS:
            errors.append(f"Driver {self.driver} is does not support the communicator, "
                          f"{self.host.communicator}, on that remote host")

        # Confirm communicator is compatible with with host type
        communicator_class = get_communicator_class(self.host.communicator)
        if self.host.type not in communicator_class.SUPPORTED_HOST_TYPES:
            errors.append(f"Communicator {self.host.communicator} is does not support the host type {self.host.type}"
                          f" of {self.host}")

        # Confirm driver is compatible with host type
        if self.host.type not in shareable_device_driver.host_driver.SUPPORTED_HOST_TYPES:
            errors.append(f"Driver {self.driver} is does not support this type of remote host, {self.host.type}.")

        errors_message = ', '.join(errors)
        if errors:
            raise ValidationError({'config_json': errors_message})


class DeviceInline(admin.TabularInline):
    model = Device
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 40})},
    }


class ResourceAdmin(admin.ModelAdmin):
    inlines = [DeviceInline]


admin.site.register(Pool)
admin.site.register(Resource, ResourceAdmin)
admin.site.register(RemoteHost)
