"""TuShare 股票日线数据 Mapper。"""

from datetime import date
from decimal import Decimal
from typing import Any

from app.modules.data_engineering.domain.entities.stock_daily import StockDaily
from app.modules.data_engineering.domain.exceptions import ExternalStockServiceError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


def _parse_date(value: Any) -> date:
    if not value:
        raise ExternalStockServiceError("Missing required field: trade_date")
    s = str(value).strip()
    if len(s) != 8 or not s.isdigit():
        raise ExternalStockServiceError(f"Invalid date format: {value!r}")
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError as e:
        raise ExternalStockServiceError(f"Invalid date: {value!r}") from e


def _parse_decimal(value: Any, field_name: str, required: bool = True) -> Decimal | None:
    if value is None:
        if required:
            raise ExternalStockServiceError(f"Missing required field: {field_name}")
        return None
    try:
        return Decimal(str(value))
    except Exception as e:
        if required:
            raise ExternalStockServiceError(f"Invalid decimal for {field_name}: {value!r}") from e
        return None


class TuShareStockDailyMapper:
    """将 TuShare 的三个接口返回的数据合并为 StockDaily。"""

    def merge_to_stock_daily(
        self,
        ts_code: str,
        daily_data: list[dict[str, Any]],
        adj_factor_data: list[dict[str, Any]],
        daily_basic_data: list[dict[str, Any]],
    ) -> list[StockDaily]:
        """按 trade_date 合并三份数据。"""
        # 使用 trade_date 字符串作为 key 建立索引
        daily_map = {str(r.get("trade_date")): r for r in daily_data if r.get("trade_date")}
        adj_map = {str(r.get("trade_date")): r for r in adj_factor_data if r.get("trade_date")}
        basic_map = {str(r.get("trade_date")): r for r in daily_basic_data if r.get("trade_date")}

        result = []
        # 以 daily 数据为基准
        for t_date, d_row in daily_map.items():
            a_row = adj_map.get(t_date, {})
            b_row = basic_map.get(t_date, {})

            parsed_date = _parse_date(t_date)

            try:
                # 必填字段
                open_val = _parse_decimal(d_row.get("open"), "open")
                high_val = _parse_decimal(d_row.get("high"), "high")
                low_val = _parse_decimal(d_row.get("low"), "low")
                close_val = _parse_decimal(d_row.get("close"), "close")
                pre_close_val = _parse_decimal(d_row.get("pre_close"), "pre_close")
                change_val = _parse_decimal(d_row.get("change"), "change")
                pct_chg_val = _parse_decimal(d_row.get("pct_chg"), "pct_chg")
                vol_val = _parse_decimal(d_row.get("vol"), "vol")
                amount_val = _parse_decimal(d_row.get("amount"), "amount")
                adj_factor_val = _parse_decimal(a_row.get("adj_factor", 1.0), "adj_factor")

                # 选填字段 (daily_basic)
                turnover_rate = _parse_decimal(b_row.get("turnover_rate"), "turnover_rate", False)
                turnover_rate_f = _parse_decimal(b_row.get("turnover_rate_f"), "turnover_rate_f", False)
                volume_ratio = _parse_decimal(b_row.get("volume_ratio"), "volume_ratio", False)
                pe = _parse_decimal(b_row.get("pe"), "pe", False)
                pe_ttm = _parse_decimal(b_row.get("pe_ttm"), "pe_ttm", False)
                pb = _parse_decimal(b_row.get("pb"), "pb", False)
                ps = _parse_decimal(b_row.get("ps"), "ps", False)
                ps_ttm = _parse_decimal(b_row.get("ps_ttm"), "ps_ttm", False)
                dv_ratio = _parse_decimal(b_row.get("dv_ratio"), "dv_ratio", False)
                dv_ttm = _parse_decimal(b_row.get("dv_ttm"), "dv_ttm", False)
                total_share = _parse_decimal(b_row.get("total_share"), "total_share", False)
                float_share = _parse_decimal(b_row.get("float_share"), "float_share", False)
                free_share = _parse_decimal(b_row.get("free_share"), "free_share", False)
                total_mv = _parse_decimal(b_row.get("total_mv"), "total_mv", False)
                circ_mv = _parse_decimal(b_row.get("circ_mv"), "circ_mv", False)

                stock = StockDaily(
                    id=None,
                    source=DataSource.TUSHARE,
                    third_code=ts_code,
                    symbol=None,  # 将在handler中填充
                    trade_date=parsed_date,
                    open=open_val,  # type: ignore
                    high=high_val,  # type: ignore
                    low=low_val,  # type: ignore
                    close=close_val,  # type: ignore
                    pre_close=pre_close_val,  # type: ignore
                    change=change_val,  # type: ignore
                    pct_chg=pct_chg_val,  # type: ignore
                    vol=vol_val,  # type: ignore
                    amount=amount_val,  # type: ignore
                    adj_factor=adj_factor_val,  # type: ignore
                    turnover_rate=turnover_rate,
                    turnover_rate_f=turnover_rate_f,
                    volume_ratio=volume_ratio,
                    pe=pe,
                    pe_ttm=pe_ttm,
                    pb=pb,
                    ps=ps,
                    ps_ttm=ps_ttm,
                    dv_ratio=dv_ratio,
                    dv_ttm=dv_ttm,
                    total_share=total_share,
                    float_share=float_share,
                    free_share=free_share,
                    total_mv=total_mv,
                    circ_mv=circ_mv,
                )
                result.append(stock)
            except ExternalStockServiceError:
                raise
            except Exception as e:
                raise ExternalStockServiceError(f"Error parsing row for {ts_code} at {t_date}: {e}") from e

        return result
