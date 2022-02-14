import pkg_resources  # part of setuptools

try:
    __version__ = pkg_resources.get_distribution("motley_cue").version
except Exception:
    __version__ = "unknown"
