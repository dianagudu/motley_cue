from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic import ValidationError

from .api_v1.api import api_router as api_router_v1
from ..dependencies import mapper, Settings
from ..mapper.exceptions import (
    validation_exception_handler,
    request_validation_exception_handler,
)


def create_app():
    """Create motley_cue api."""

    settings = Settings(docs_url=mapper.config.docs_url)
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
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, validation_exception_handler)

    app.include_router(api_router_v1, prefix="", tags=["API"])
    app.include_router(api_router_v1, prefix=settings.API_V1_STR, tags=["API v1"])
    app.include_router(
        api_router_v1, prefix=settings.API_LATEST_STR, tags=["API latest"]
    )

    return app


api = create_app()
