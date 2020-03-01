import json
from datetime import datetime
from json import JSONDecodeError

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
# Create your models here.
from django.db.models import Q, Count
from django.forms import Textarea
from django.utils.functional import lazy

from quartermaster.AbstractShareableUsbDevice import AbstractShareableUsbDevice
from quartermaster.helpers import get_driver_obj


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


def loaded_drivers():
    return sorted(list(((driver.__name__, driver.__name__) for driver in AbstractShareableUsbDevice.__subclasses__())))


class DeviceHideOfflineManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(online=True)


class Device(models.Model):
    """
    Device represents a single USB resource that is being made available from a remote host
    """
    resource = models.ForeignKey(Resource, blank=False, null=True, on_delete=models.CASCADE)
    # Choices for `driver` are set dynamically set when the admin form is displayed. This is because
    # when the model is loaded not all the apps are online so we can yet probe for installed drivers
    driver = models.CharField(blank=False, null=False, max_length=100,
                              choices=lazy(loaded_drivers, list)())
    config_json = models.TextField()
    name = models.SlugField(blank=False, null=False, max_length=30, primary_key=True)
    online = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self._meta.get_field('driver').choices = self.loaded_drivers()

    def __str__(self):
        return f"{str(self.resource)} / {self.name}"

    everything = models.Manager()

    objects = DeviceHideOfflineManager()

    @property
    def config(self):
        return json.loads(self.config_json)

    def set_config(self, config: dict):
        self.config_json = json.dumps(config)

    @property
    def in_use(self) -> bool:
        return self.resource.in_use

    def get_driver(self):
        return get_driver_obj(self)

    def clean(self):
        # Check valid driver is used
        try:
            driver: AbstractShareableUsbDevice = self.get_driver()
        except JSONDecodeError as e:
            raise ValidationError({'config_json': f"Invalid JSON, {e.msg}"})
        errors = driver.validate_configuration()
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
