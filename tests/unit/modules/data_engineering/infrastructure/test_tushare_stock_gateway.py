"""TuShareStockGateway 单测：字段映射、list_date 解析、解析失败则整批抛错。"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.data_engineering.domain.exceptions import ExternalStockServiceError
from app.modules.data_engineering.domain.stock_basic import DataSource, StockBasic, StockStatus
from app.modules.data_engineering.infrastructure.tushare_stock_gateway import TuShareStockGateway


class TestTuShareStockGatewayMapping:
    """字段映射：ts_code→third_code、list_status→StockStatus、list_date 解析。"""

    @pytest.mark.asyncio
    async def test_fetch_stock_basic_returns_list_of_stock_basic(self) -> None:
        """正常返回时每条为 StockBasic，ts_code→third_code，list_status L→LISTED。"""
        mock_data = [
            {
                "ts_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "market": "深圳",
                "area": "深圳",
                "industry": "银行",
                "list_date": "20100101",
                "list_status": "L",
            }
        ]
        with patch.object(
            TuShareStockGateway, "_fetch_raw", new_callable=AsyncMock, return_value=mock_data
        ):
            gateway = TuShareStockGateway(token="test-token")
            result = await gateway.fetch_stock_basic()
        assert len(result) == 1
        stock = result[0]
        assert isinstance(stock, StockBasic)
        assert stock.third_code == "000001.SZ"
        assert stock.symbol == "000001"
        assert stock.name == "平安银行"
        assert stock.status == StockStatus.LISTED
        assert stock.source == DataSource.TUSHARE
        assert stock.list_date == date(2010, 1, 1)

    @pytest.mark.asyncio
    async def test_list_status_d_maps_to_delisted(self) -> None:
        mock_data = [
            {
                "ts_code": "000002.SZ",
                "symbol": "000002",
                "name": "已退市",
                "market": "深圳",
                "area": "深圳",
                "industry": "其他",
                "list_date": "19910101",
                "list_status": "D",
            }
        ]
        with patch.object(
            TuShareStockGateway, "_fetch_raw", new_callable=AsyncMock, return_value=mock_data
        ):
            gateway = TuShareStockGateway(token="test-token")
            result = await gateway.fetch_stock_basic()
        assert result[0].status == StockStatus.DELISTED

    @pytest.mark.asyncio
    async def test_list_status_p_maps_to_suspended(self) -> None:
        mock_data = [
            {
                "ts_code": "600000.SH",
                "symbol": "600000",
                "name": "浦发",
                "market": "上海",
                "area": "上海",
                "industry": "银行",
                "list_date": "19991110",
                "list_status": "P",
            }
        ]
        with patch.object(
            TuShareStockGateway, "_fetch_raw", new_callable=AsyncMock, return_value=mock_data
        ):
            gateway = TuShareStockGateway(token="test-token")
            result = await gateway.fetch_stock_basic()
        assert result[0].status == StockStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_invalid_list_date_raises_external_error(self) -> None:
        """任一条 list_date 非法则整批抛 ExternalStockServiceError。"""
        mock_data = [
            {
                "ts_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "market": "深圳",
                "area": "深圳",
                "industry": "银行",
                "list_date": "not-a-date",
                "list_status": "L",
            }
        ]
        with patch.object(
            TuShareStockGateway, "_fetch_raw", new_callable=AsyncMock, return_value=mock_data
        ):
            gateway = TuShareStockGateway(token="test-token")
            with pytest.raises(ExternalStockServiceError):
                await gateway.fetch_stock_basic()

    @pytest.mark.asyncio
    async def test_missing_required_field_raises_external_error(self) -> None:
        """必填字段缺失时整批抛错。"""
        mock_data = [
            {
                "ts_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "market": "深圳",
                "area": "深圳",
                "industry": "银行",
                "list_status": "L",
                # list_date 缺失
            }
        ]
        with patch.object(
            TuShareStockGateway, "_fetch_raw", new_callable=AsyncMock, return_value=mock_data
        ):
            gateway = TuShareStockGateway(token="test-token")
            with pytest.raises(ExternalStockServiceError):
                await gateway.fetch_stock_basic()
