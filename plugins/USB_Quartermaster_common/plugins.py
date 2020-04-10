import importlib
import inspect
import pkgutil
from functools import lru_cache
from types import ModuleType
from typing import Dict, Type, Any, Callable, List

from USB_Quartermaster_common import AbstractCommunicator, AbstractRemoteHostDriver, AbstractShareableDeviceDriver

from USB_Quartermaster_common import AbstractLocalDriver


@lru_cache
def find_all_plugins() -> Dict[str, ModuleType]:
    discovered_plugins = {
        name: importlib.import_module(name)
        for finder, name, ispkg
        in pkgutil.iter_modules()
        if name.startswith('USB_Quartermaster_') and name != "USB_Quartermaster_common"
    }
    return discovered_plugins


def class_tester(thing: Any, parent_class: Type) -> bool:
    return inspect.isclass(thing) and issubclass(thing, parent_class)


def get_plugin_classes(matcher: Callable) -> List[Type[Any]]:
    all_found = []
    for plugin in find_all_plugins().values():
        found = dict(inspect.getmembers(plugin, matcher)).values()
        all_found.extend(found)
    return all_found


def is_communicator(thing) -> bool:
    return class_tester(thing, AbstractCommunicator)


def is_remote_host_driver(thing) -> bool:
    return class_tester(thing, AbstractRemoteHostDriver)


def is_shareable_device_driver(thing) -> bool:
    return class_tester(thing, AbstractShareableDeviceDriver)

def is_local_driver(thing) -> bool:
    return class_tester(thing, AbstractLocalDriver)

@lru_cache
def communicator_classes() -> List[Type[AbstractCommunicator]]:
    return get_plugin_classes(is_communicator)


@lru_cache
def remote_host_classes() -> List[Type[AbstractRemoteHostDriver]]:
    return get_plugin_classes(is_remote_host_driver)


@lru_cache
def shareable_device_classes() -> List[Type[AbstractShareableDeviceDriver]]:
    return get_plugin_classes(is_shareable_device_driver)

@lru_cache
def local_driver_classes() -> List[Type[AbstractLocalDriver]]:
    return get_plugin_classes(is_local_driver)
