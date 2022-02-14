from typing import Optional
from pydantic import BaseSettings

from .version import __version__
from .mapper import Mapper


class Settings(BaseSettings):
    title: str = "motley_cue"
    description: str = "A service for mapping OIDC identities to local identities"
    version: str =__version__
    openapi_url: str = "/openapi.json"
    docs_url: Optional[str] = None
    redoc_url: Optional[str] = None


mapper = Mapper()
settings = Settings(docs_url=mapper.config.docs_url)  # only the Swagger docs can be enabled and configured, ReDoc is disabled
