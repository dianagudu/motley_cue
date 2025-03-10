"""exceptions definitions for motley_cue"""

from typing import Union
from pydantic import ValidationError
from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.responses import JSONResponse
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
            + "; ".join(
                f"{e['msg']} ({(' -> '.join(str(l) for l in e['loc']))})"
                for e in errors
            )
        )
        super().__init__(status_code=HTTP_400_BAD_REQUEST, content={"detail": message})


class InvalidResponse(JSONResponse):
    """Response for invalid response model.

    Returns HTTP 500 Internal Server Error status code
    and informative message.
    """

    def __init__(self, exc: Union[ResponseValidationError, ValidationError]):
        message = "Could not validate response model."
        _ = exc
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": message}
        )


class InternalException(Exception):
    """Wrapper for internal errors"""

    def __init__(self, message) -> None:
        self.message = message
        super().__init__(message)
