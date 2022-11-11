"""exceptions definitions for motley_cue
"""
from pydantic import ValidationError
from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


class Unauthorised(HTTPException):
    """Wrapper for HTTP Unauthorized error."""

    def __init__(self, message: str):
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, detail=message)


class BadRequest(HTTPException):
    """Wrapper for HTTP Bad Request error."""

    def __init__(self, message: str):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, detail=message)


class InternalServerError(HTTPException):
    """Wrapper for HTTP 500 Internal Server Error."""

    def __init__(self, message):
        super().__init__(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


class NotFound(HTTPException):
    """Wrapper for HTTP Not Found error."""

    def __init__(self, message: str):
        super().__init__(status_code=HTTP_404_NOT_FOUND, detail=message)


class MissingParameter(JSONResponse):
    """Response for missing query parameters.

    Returns HTTP 400 Bad Request status code
    and informative message.
    """

    def __init__(self, exc: RequestValidationError):
        errors = exc.errors()
        no_errors = len(errors)
        message = (
            f"{no_errors} request validation error{'' if no_errors == 1 else 's'}: "
            + "; ".join(f"{e['msg']} ({(' -> '.join(str(l) for l in e['loc']))})" for e in errors)
        )
        super().__init__(status_code=HTTP_400_BAD_REQUEST, content={"detail": message})


class InternalException(Exception):
    """Wrapper for internal errors"""

    def __init__(self, message) -> None:
        self.message = message
        super().__init__(message)


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Replacement callback for handling RequestValidationError exceptions.

    :param request: request object that caused the RequestValidationError
    :param exc: RequestValidationError containing validation errors
    """
    _ = request
    _ = exc
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Could not validate response model."},
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Replacement callback for handling RequestValidationError exceptions.

    :param request: request object that caused the RequestValidationError
    :param exc: RequestValidationError containing validation errors
    """
    _ = request
    return MissingParameter(exc)
