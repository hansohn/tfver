import platform
import sys
from typing import Dict


def get_platform() -> Dict[str, str]:
    """
    Query local os and arch values and return as dict
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    is_64bits = sys.maxsize > 2**32

    data = {}
    data["os"] = system

    if machine == "x86_64":
        if not is_64bits:
            data["arch"] = "386"
        elif is_64bits:
            data["arch"] = "amd64"
    elif machine == "aarch64":
        if not is_64bits:
            data["arch"] = "arm"
        elif is_64bits:
            data["arch"] = "arm64"

    return data


if __name__ == "__main__":
    print(get_platform())
