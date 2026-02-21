"""StockDaily → 持久化行映射，供 SQLAlchemy upsert 使用。"""

from app.modules.data_engineering.domain.entities.stock_daily import StockDaily


class StockDailyPersistenceMapper:
    """将 StockDaily 转为 upsert 用的 dict（不含 id/created_at/updated_at/version）。"""

    def to_row(self, entity: StockDaily) -> dict:
        """领域实体 → 插入/更新用字典。"""
        return {
            "source": entity.source.value,
            "third_code": entity.third_code,
            "symbol": entity.symbol,
            "trade_date": entity.trade_date,
            "open": entity.open,
            "high": entity.high,
            "low": entity.low,
            "close": entity.close,
            "pre_close": entity.pre_close,
            "change": entity.change,
            "pct_chg": entity.pct_chg,
            "vol": entity.vol,
            "amount": entity.amount,
            "adj_factor": entity.adj_factor,
            "turnover_rate": entity.turnover_rate,
            "turnover_rate_f": entity.turnover_rate_f,
            "volume_ratio": entity.volume_ratio,
            "pe": entity.pe,
            "pe_ttm": entity.pe_ttm,
            "pb": entity.pb,
            "ps": entity.ps,
            "ps_ttm": entity.ps_ttm,
            "dv_ratio": entity.dv_ratio,
            "dv_ttm": entity.dv_ttm,
            "total_share": entity.total_share,
            "float_share": entity.float_share,
            "free_share": entity.free_share,
            "total_mv": entity.total_mv,
            "circ_mv": entity.circ_mv,
        }
