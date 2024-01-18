import logging
import pkgutil
import importlib
from typing import Union
from pydantic import ValidationError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError

from motley_cue.dependencies import mapper, Settings
from motley_cue.mapper.exceptions import (
    InternalException,
    InvalidResponse,
    MissingParameter,
)
import motley_cue.apis

logger = logging.getLogger(__name__)

# API settings
settings = Settings(
    docs_url=mapper.config.docs_url,
    redoc_url=mapper.config.redoc_url,
    api_version=mapper.config.api_version,
)

# create FastAPI app
api = FastAPI(
    title=settings.title,
    description=settings.description,
    version=settings.version,
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
)

# get routers for all api versions
api_routers = {}
for version_submodule in pkgutil.iter_modules(motley_cue.apis.__path__):
    if version_submodule.name.startswith("v"):
        try:
            api_routers[version_submodule.name] = importlib.import_module(
                f"motley_cue.apis.{version_submodule.name}.api"
            ).router
        except AttributeError as exc:
            logger.error(
                "API version %s does not have a router",
                version_submodule.name,
                exc_info=exc,
            )
            raise InternalException(
                f"API version {version_submodule.name} does not have a router."
            ) from exc
        except Exception as exc:
            logger.error(
                "Could not import API version %s",
                version_submodule.name,
                exc_info=exc,
            )
            raise InternalException(
                f"Could not import API version {version_submodule.name}"
            ) from exc

try:
    current_api_router = api_routers[settings.api_version]
except KeyError as exc:
    raise InternalException(
        f"API version {settings.api_version} does not exist."
    ) from exc

# current API version
api.include_router(current_api_router, prefix="/api", tags=["API"])
# for compatibility with old API, include all endpoints in the root
api.include_router(current_api_router, prefix="", include_in_schema=False)

# all API versions
for api_version, api_router in api_routers.items():
    api.include_router(
        api_router, prefix=f"/api/{api_version}", tags=[f"API {api_version}"]
    )

# Logo for redoc. This must be at the end after all the routes have been set!
api.openapi()["info"]["x-logo"] = {
    "url": "https://motley-cue.readthedocs.io/en/latest/_static/logos/motley-cue.png"
}


# Exception handlers
@api.exception_handler(ResponseValidationError)
@api.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, validation_exc: Union[ResponseValidationError, ValidationError]
):
    """Replacement callback for handling ResponseValidationError exceptions.

    :param request: request object that caused the ResponseValidationError
    :param validation_exc: ResponseValidationError containing validation errors
    """
    _ = request
    _ = validation_exc
    return InvalidResponse(validation_exc)


@api.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, validation_exc: RequestValidationError
):
    """Replacement callback for handling RequestValidationError exceptions.

    :param request: request object that caused the RequestValidationError
    :param validation_exc: RequestValidationError containing validation errors
    """
    _ = request
    return MissingParameter(validation_exc)
