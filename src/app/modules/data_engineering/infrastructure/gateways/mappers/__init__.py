"""Gateways 层映射：外部 API 响应 → 领域模型。"""

from .akshare_concept_mapper import AkShareConceptMapper
from .tushare_stock_basic_mapper import TuShareStockBasicMapper

__all__ = ["AkShareConceptMapper", "TuShareStockBasicMapper"]
