"""单元测试：StockBasic 实体与 StockStatus、DataSource 枚举。"""

from datetime import date, datetime

from app.modules.data_engineering.domain.stock_basic import (
    DataSource,
    StockBasic,
    StockStatus,
)


class TestStockStatus:
    def test_listed_value(self) -> None:
        assert StockStatus.LISTED.value == "L"

    def test_delisted_value(self) -> None:
        assert StockStatus.DELISTED.value == "D"

    def test_suspended_value(self) -> None:
        assert StockStatus.SUSPENDED.value == "P"


class TestDataSource:
    def test_tushare_value(self) -> None:
        assert DataSource.TUSHARE.value == "TUSHARE"


class TestStockBasic:
    def test_entity_has_required_business_fields(self) -> None:
        stock = StockBasic(
            id=None,
            created_at=datetime(2020, 1, 1),
            updated_at=datetime(2020, 1, 1),
            version=0,
            source=DataSource.TUSHARE,
            third_code="000001.SZ",
            symbol="000001",
            name="平安银行",
            market="深圳",
            area="深圳",
            industry="银行",
            list_date=date(2010, 1, 1),
            status=StockStatus.LISTED,
        )
        assert stock.third_code == "000001.SZ"
        assert stock.symbol == "000001"
        assert stock.name == "平安银行"
        assert stock.status == StockStatus.LISTED
        assert stock.list_date == date(2010, 1, 1)

    def test_list_date_is_date_type(self) -> None:
        list_date = date(2015, 6, 1)
        stock = StockBasic(
            id=None,
            created_at=datetime(2020, 1, 1),
            updated_at=datetime(2020, 1, 1),
            version=0,
            source=DataSource.TUSHARE,
            third_code="600000.SH",
            symbol="600000",
            name="浦发银行",
            market="上海",
            area="上海",
            industry="银行",
            list_date=list_date,
            status=StockStatus.LISTED,
        )
        assert stock.list_date is list_date
        assert isinstance(stock.list_date, date)

    def test_status_is_stock_status_enum(self) -> None:
        stock = StockBasic(
            id=None,
            created_at=datetime(2020, 1, 1),
            updated_at=datetime(2020, 1, 1),
            version=0,
            source=DataSource.TUSHARE,
            third_code="000001.SZ",
            symbol="000001",
            name="平安银行",
            market="深圳",
            area="深圳",
            industry="银行",
            list_date=date(2010, 1, 1),
            status=StockStatus.SUSPENDED,
        )
        assert stock.status is StockStatus.SUSPENDED
