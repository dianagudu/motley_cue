import os
import pkgutil
import importlib
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic import ValidationError

from motley_cue.dependencies import mapper, Settings
from motley_cue.mapper.exceptions import (
    InternalException,
    validation_exception_handler,
    request_validation_exception_handler,
)


def create_app():
    """Create motley_cue api."""

    settings = Settings(
        docs_url=mapper.config.docs_url,
        redoc_url=mapper.config.redoc_url,
        api_version=mapper.config.api_version,
    )
    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
    )
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, validation_exception_handler)

    # get routers for all api versions
    api_routers = {}
    for version_submodule in pkgutil.iter_modules([os.path.dirname(__file__)]):
        if version_submodule.name.startswith("v"):
            api_routers[version_submodule.name] = importlib.import_module(
                f"motley_cue.api.{version_submodule.name}"
            ).router

    try:
        current_api_router = api_routers[settings.api_version]
    except KeyError as exc:
        raise InternalException(
            f"API version {settings.api_version} does not exist."
        ) from exc

    # current API version
    app.include_router(current_api_router, prefix="/api", tags=["API"])
    # for compatibility with old API, include all endpoints in the root
    app.include_router(current_api_router, prefix="", include_in_schema=False)

    # all API versions
    for api_version, api_router in api_routers.items():
        app.include_router(
            api_router, prefix=f"/api/{api_version}", tags=[f"API {api_version}"]
        )

    # Logo for redoc. This must be at the end after all the routes have been set!
    app.openapi()["info"]["x-logo"] = {
        "url": "https://motley-cue.readthedocs.io/en/latest/_static/logos/motley-cue.png"
    }

    return app


api = create_app()
