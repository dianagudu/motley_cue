from typing import Optional
from pydantic import BaseSettings, validator

from .version import __version__
from .mapper import Mapper, Config


class Settings(BaseSettings):
    title: str = "motley_cue"
    description: str = "A service for mapping OIDC identities to local identities"
    version: str =__version__
    openapi_url: str = "/openapi.json"
    docs_url: Optional[str] = None
    redoc_url: Optional[str] = None

    @validator("openapi_url", allow_reuse=True)
    def must_start_with_slash(cls, url):
        if not url.startswith("/"):
            raise ValueError("Routed paths must start with '/'")
        return url

    @validator("docs_url", "redoc_url", allow_reuse=True)
    def must_start_with_slash_or_none(cls, url):
        if url is not None and not url.startswith("/"):
            raise ValueError("Routed paths must start with '/'")
        return url


mapper = Mapper(Config.from_files([]))
