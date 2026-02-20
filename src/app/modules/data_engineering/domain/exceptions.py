"""领域异常，供网关解析/网络失败时抛出。"""

from app.shared_kernel.domain.exception import DomainException
from app.shared_kernel.domain.exception import NotFoundException


class ExternalStockServiceError(DomainException):
    """外部股票数据源拉取或解析失败。"""

    pass


class ExternalConceptServiceError(DomainException):
    """AKShare 概念板块数据源拉取或解析失败。"""

    pass


class ConceptNotFoundError(NotFoundException):
    """查询的概念板块不存在。"""

    pass
