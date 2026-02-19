"""领域异常，供网关解析/网络失败时抛出。"""

from app.shared_kernel.domain.exception import DomainException


class ExternalStockServiceError(DomainException):
    """外部股票数据源拉取或解析失败。"""

    pass
