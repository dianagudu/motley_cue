"""Module containing global mapper object created from default configuration files."""

from typing import Optional
from pydantic import field_validator

from motley_cue._version import __version__
from motley_cue.mapper import Mapper, Config
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings class with default values for motley_cue API."""

    # pylint: disable=no-self-use, no-self-argument
    title: str = "motley_cue"
    description: str = "A service for mapping OIDC identities to local identities"
    version: str = __version__
    openapi_url: str = "/openapi.json"
    docs_url: Optional[str] = None
    redoc_url: Optional[str] = None
    api_version: str = "v1"

    @field_validator("openapi_url")
    @classmethod
    def must_start_with_slash(cls, url):
        """validate URLs: must start with a '/'"""
        if not url.startswith("/"):
            raise ValueError("Routed paths must start with '/'")
        return url

    @field_validator("docs_url", "redoc_url")
    @classmethod
    def must_start_with_slash_or_none(cls, url):
        """validate URLs: must start with a '/' or be None."""
        if url is not None and not url.startswith("/"):
            raise ValueError("Routed paths must start with '/'")
        return url

    @field_validator("api_version")
    @classmethod
    def must_start_with_v(cls, version):
        """validate API version: must start with a 'v'"""
        if not version.startswith("v"):
            raise ValueError("API version must start with 'v'")
        return version


mapper = Mapper(Config.from_files([]))
