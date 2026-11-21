import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import Error
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)

SQL_ERRORS = {
    "EXY01": (422, "OPENING_DOES_NOT_FIT"),
    "EXY02": (422, "ITEM_OUTSIDE_ROOM"),
    "EXY03": (422, "WALL_ROOM_LIMIT"),
    "EXY04": (409, "REVISION_LOCKED"),
    "EXY05": (422, "SCALE_UNDETERMINED"),
    "EXY06": (409, "OPEN_REVIEW_FLAGS"),
    "EXY07": (409, "SCALE_NOT_CONFIRMED"),
    "EXY08": (409, "UPLOAD_NOT_READY"),
    "EXY09": (422, "INVALID_EDIT"),
    "EXY10": (404, "SHARE_LINK_INVALID"),
}


class ApiError(Exception):
    def __init__(self, status: int, name: str, message: str):
        super().__init__(message)
        self.status = status
        self.name = name


def error_response(status: int, name: str, message: str) -> JSONResponse:
    return JSONResponse({"error": name, "message": message}, status_code=status)


async def api_error(_request: Request, error: ApiError) -> JSONResponse:
    return error_response(error.status, error.name, str(error))


async def unexpected_error(_request: Request, error: Exception) -> JSONResponse:
    logger.error("Unhandled API error", exc_info=error)
    return error_response(500, "INTERNAL_ERROR", "An internal error occurred.")


async def database_error(request: Request, error: Error) -> JSONResponse:
    if mapped := SQL_ERRORS.get(error.sqlstate):
        status, name = mapped
        return error_response(status, name, error.diag.message_primary or name)
    return await unexpected_error(request, error)


async def invalid_request(_request: Request, _error: RequestValidationError) -> JSONResponse:
    return error_response(422, "INVALID_REQUEST", "Invalid request parameters.")


async def http_error(_request: Request, error: HTTPException) -> JSONResponse:
    name = {401: "AUTH_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND"}.get(
        error.status_code, "HTTP_ERROR"
    )
    message = error.detail if isinstance(error.detail, str) else "Request failed."
    response = error_response(error.status_code, name, message)
    response.headers.update(error.headers or {})
    return response


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error)
    app.add_exception_handler(Error, database_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, unexpected_error)
