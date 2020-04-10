from importlib import import_module
from pathlib import Path
from typing import Dict


def get_ci_properties() -> Dict[str, str]:
    final_properties = {}
    for file in Path(__file__).absolute().parent.iterdir():
        if file.is_file() and file.name.endswith('.py') and file.name not in ['__init__.py']:
            module_name = file.name[:-3]
            module = import_module(f".{module_name}", package=f"client.ci")
            func = getattr(module, 'detect_properties')
            detected_props = func()
            final_properties.update(detected_props)
    print(final_properties)
    return final_properties
