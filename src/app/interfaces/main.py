from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.responses import Response

from app.config import settings
from app.interfaces.exception_handler import (
    domain_exception_handler,
    general_exception_handler,
    validation_exception_handler,
)
from app.interfaces.middleware import setup_middleware
from app.interfaces.module_registry import register_modules
from app.interfaces.response import ApiResponse
from app.shared_kernel.application.mediator import Mediator
from app.shared_kernel.domain.exception import DomainException
from app.shared_kernel.infrastructure.database import Database
from app.shared_kernel.infrastructure.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _register_handlers(mediator: Mediator, db: Database) -> None:
    """Register all module command/query handlers with the mediator."""
    # 各模块的 command/query 若需通过 Mediator 分发，在此注册


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(log_level=settings.LOG_LEVEL, app_env=settings.APP_ENV)
    logger.info("Application starting up", app_name=settings.APP_NAME, env=settings.APP_ENV)

    db = Database(url=settings.DATABASE_URL, echo=False)
    app.state.db = db

    mediator = Mediator()
    _register_handlers(mediator, db)
    app.state.mediator = mediator

    yield

    await db.dispose()
    logger.info("Application shut down")


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_DEBUG else None,
    redoc_url="/redoc" if settings.APP_DEBUG else None,
)

setup_middleware(app)

_ExceptionHandler = Callable[..., Awaitable[Response]]
app.add_exception_handler(DomainException, cast(_ExceptionHandler, domain_exception_handler))
app.add_exception_handler(
    RequestValidationError, cast(_ExceptionHandler, validation_exception_handler)
)
app.add_exception_handler(Exception, general_exception_handler)

register_modules(app)


@app.get("/health", response_model=ApiResponse[dict])
async def health_check() -> ApiResponse[dict]:
    return ApiResponse.success(data={"status": "healthy"})
