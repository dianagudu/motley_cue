"""Module that loads the version of the installed motley_cue package.
"""
import pkg_resources  # part of setuptools

try:
    __version__ = pkg_resources.get_distribution("motley_cue").version
except Exception:  # pylint: disable=broad-except
    __version__ = "unknown"
