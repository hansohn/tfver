__all__ = ['version']

try:
    import importlib_metadata as metadata
except ImportError:
    from importlib import metadata  # type: ignore[no-redef]

try:
    version = metadata.version('tfrelease')
except metadata.PackageNotFoundError:
    import logging

    log = logging.getLogger(__name__)
    log.warning("Package metadata could not be found. Overriding it with version found in setup.py")
    from setup import version

del metadata
