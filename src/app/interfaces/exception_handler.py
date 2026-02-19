import traceback
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.interfaces.response import ApiResponse
from app.shared_kernel.domain.exception import (
    DomainException,
    NotFoundException,
    ValidationException,
)
from app.shared_kernel.infrastructure.logging import get_logger

logger = get_logger(__name__)


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    if isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_400_BAD_REQUEST

    response: ApiResponse[Any] = ApiResponse.error(code=status_code, message=exc.message)
    return JSONResponse(content=response.model_dump(), status_code=status_code)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    error_messages = []
    for err in errors:
        loc = " -> ".join([str(x) for x in err["loc"] if x != "body"])
        error_messages.append(f"{loc}: {err['msg']}")

    message = "; ".join(error_messages) if error_messages else "Validation error"
    response: ApiResponse[Any] = ApiResponse.error(
        code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message
    )
    return JSONResponse(
        content=response.model_dump(), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", exc_info=True, traceback=traceback.format_exc())
    response: ApiResponse[Any] = ApiResponse.error(
        code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Internal server error"
    )
    return JSONResponse(
        content=response.model_dump(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
