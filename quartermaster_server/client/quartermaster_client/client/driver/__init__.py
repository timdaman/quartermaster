# import pkgutil
# from importlib import import_module
# from pathlib import Path

from .LocalDriver import LocalDriver
from .UsbipOverSSH import UsbipOverSSH
from .VirtualHereOverSSH import VirtualHereOverSSH
# 
# for mod in pkgutil.iter_modules('.'):
#     print(mod)
#     # if file.is_file() and file.name.endswith('.py') and file.name not in ['LocalDriver.py', '__init__.py']:
#     #     module_name = file.name[:-3]
#     #     import_module(f".{module_name}", package=f"client.driver")
# TODO: Replace sleep and subprocess with async versions
# TODO: Find drivers automatically
