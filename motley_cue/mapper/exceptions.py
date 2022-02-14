from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR


class Unauthorised(HTTPException):
    """Wrapper for HTTP Unauthorized error.
    """
    def __init__(self, message: str):
        super().__init__(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=message
        )


class BadRequest(HTTPException):
    """Wrapper for HTTP Bad Request error.
    """
    def __init__(self, message: str):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            detail=message
        )


class InternalServerError(HTTPException):
    """Wrapper for HTTP 500 Internal Server Error.
    """
    def __init__(self, message):
        super().__init__(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


class MissingParameter(JSONResponse):
    """Response for missing query parameters.

    Returns HTTP 400 Bad Request status code
    and informative message.
    """
    def __init__(self, exc: RequestValidationError):
        print(str(exc), exc.errors())
        errors = exc.errors()
        no_errors = len(errors)
        message = f"{no_errors} request validation error{'' if no_errors == 1 else 's'}: " + \
                  "; ".join(
                      f"{e['msg']} ({(' -> '.join(str(l) for l in e['loc']))})"
                  for e in errors)
        super().__init__(status_code=HTTP_400_BAD_REQUEST, content={"detail": message})


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Replacement callback for handling RequestValidationError exceptions.

    :param request: request object that caused the RequestValidationError
    :param exc: RequestValidationError containing validation errors
    """
    return MissingParameter(exc)
