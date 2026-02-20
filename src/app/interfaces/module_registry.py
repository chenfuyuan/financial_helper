"""模块注册器：统一管理各业务模块的 Router 注册，避免 main.py 硬编码每个模块的 import。"""

from fastapi import APIRouter, FastAPI


def _collect_module_routers() -> list[tuple[APIRouter, str]]:
    """收集所有模块的 Router 及其前缀。新增模块时在此追加即可，main.py 无需修改。"""
    from app.modules.data_engineering.interfaces.api.stock_basic_router import (
        router as stock_basic_router,
    )
    from app.modules.data_engineering.interfaces.api.stock_daily_router import (
        router as stock_daily_router,
    )
    from app.modules.data_engineering.interfaces.api.finance_indicator_router import (
        router as finance_indicator_router,
    )
    from app.modules.data_engineering.interfaces.api.concept_router import (
        router as concept_router,
    )

    return [
        (stock_basic_router, "/api/v1"),
        (stock_daily_router, "/api/v1"),
        (finance_indicator_router, "/api/v1"),
        (concept_router, "/api/v1"),
    ]


def register_modules(app: FastAPI) -> None:
    """将所有模块的 Router 注册到 FastAPI 应用。由 main.py 调用。"""
    for router, prefix in _collect_module_routers():
        app.include_router(router, prefix=prefix)
