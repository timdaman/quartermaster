import configparser
import os
from pathlib import Path
from typing import Dict


def detect_properties() -> Dict[str, str]:
    props = {}

    if 'TEAMCITY_BUILD_PROPERTIES_FILE' not in os.environ:
        return props

    # Support for teamcity
    prop_path = Path(os.environ['TEAMCITY_BUILD_PROPERTIES_FILE'])
    print("Detected Teamcity Build environment, loading build properties file")
    config = configparser.ConfigParser(interpolation=None)

    # What is this doing?
    # Config Parser parses INI files and requires all config keys to be in a section.
    # This prepends a fake section header, [global], to allow using that config parser library
    config_string = '[global]\n' + prop_path.read_text(encoding='utf-8')
    config.read_string(config_string)
    config = config['global']

    props['reservation_message'] = f"Teamcity_ID={config['teamcity.build.id']}"

    if len(props.keys()) > 0:
        print(f"Teamcity properties loaded {props}")
    return props
