"""股票财务指标 SQLAlchemy 模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.shared_kernel.infrastructure.database import Base

_N44 = Numeric(24, 4)  # 每股/比率类
_N46 = Numeric(24, 6)  # 大金额类


class StockFinancialModel(Base):
    """表 stock_financial：A 股财务指标，来自 Tushare fina_indicator 接口。
    UNIQUE(source, third_code, end_date)。

    Attributes:
        id: 主键，自增。
        source: 数据来源（如 Tushare），存枚举值。
        third_code: 第三方数据源中的股票代码。
        symbol: 股票标准代码标识符。
        ann_date: 公告日期。
        end_date: 报告期截止日（唯一键组成部分）。
        eps: 基本每股收益。
        dt_eps: 稀释每股收益。
        total_revenue_ps: 每股营业总收入。
        revenue_ps: 每股营业收入。
        capital_rese_ps: 每股资本公积。
        surplus_rese_ps: 每股盈余公积。
        undist_profit_ps: 每股未分配利润。
        extra_item: 非经常性损益。
        profit_dedt: 扣除非经常性损益后净利润（大金额）。
        gross_margin: 毛利润（大金额）。
        current_ratio: 流动比率。
        quick_ratio: 速动比率。
        cash_ratio: 保守速动比率。
        ar_turn: 应收账款周转率。
        ca_turn: 流动资产周转率。
        fa_turn: 固定资产周转率。
        assets_turn: 总资产周转率。
        op_income: 经营活动净收益（大金额）。
        ebit: 息税前利润（大金额）。
        ebitda: 息税折旧摊销前利润（大金额）。
        fcff: 企业自由现金流量（大金额）。
        fcfe: 股权自由现金流量（大金额）。
        current_exint: 无息流动负债（大金额）。
        noncurrent_exint: 无息非流动负债（大金额）。
        interestdebt: 带息债务（大金额）。
        netdebt: 净债务（大金额）。
        tangible_asset: 有形资产（大金额）。
        working_capital: 营运资金（大金额）。
        networking_capital: 营运流动资本（大金额）。
        invest_capital: 全部投入资本（大金额）。
        retained_earnings: 留存收益（大金额）。
        diluted2_eps: 期末摊薄每股收益。
        bps: 每股净资产。
        ocfps: 每股经营活动产生的现金流量净额。
        retainedps: 每股留存收益。
        cfps: 每股现金流量净额。
        ebit_ps: 每股息税前利润。
        fcff_ps: 每股企业自由现金流量。
        fcfe_ps: 每股股权自由现金流量。
        netprofit_margin: 销售净利率。
        grossprofit_margin: 销售毛利率。
        cogs_of_sales: 销售成本率。
        expense_of_sales: 销售期间费用率。
        profit_to_gr: 净利润/营业总收入。
        saleexp_to_gr: 销售费用/营业总收入。
        adminexp_to_gr: 管理费用/营业总收入。
        finaexp_to_gr: 财务费用/营业总收入。
        impai_ttm: 资产减值损失/营业总收入。
        gc_of_gr: 营业总成本/营业总收入。
        op_of_gr: 营业利润/营业总收入。
        ebit_of_gr: 息税前利润/营业总收入。
        roe: 净资产收益率。
        roe_waa: 加权平均净资产收益率。
        roe_dt: 净资产收益率(扣除非经常损益)。
        roa: 总资产报酬率。
        npta: 总资产净利润。
        roic: 投入资本回报率。
        roe_yearly: 年化净资产收益率。
        roa2_yearly: 年化总资产报酬率。
        debt_to_assets: 资产负债率。
        assets_to_eqt: 权益乘数。
        dp_assets_to_eqt: 权益乘数(杜邦分析)。
        ca_to_assets: 流动资产/总资产。
        nca_to_assets: 非流动资产/总资产。
        tbassets_to_totalassets: 有形资产/总资产。
        int_to_talcap: 带息债务/全部投入资本。
        eqt_to_talcap: 股东权益/全部投入资本。
        currentdebt_to_debt: 流动负债/负债合计。
        longdeb_to_debt: 非流动负债/负债合计。
        ocf_to_shortdebt: 经营现金流/流动负债。
        ocf_to_interestdebt: 经营现金流/带息债务。
        ocf_to_debt: 经营现金流/负债合计。
        cash_to_liqdebt: 货币资金/流动负债。
        cash_to_liqdebt_withinterest: 货币资金/带息流动负债。
        op_to_liqdebt: 经营现金流/流动负债。
        op_to_debt: 经营现金流/负债合计。
        roic_yearly: 年化投入资本回报率。
        profit_to_op: 净利润/经营活动净收益。
        q_opincome: 经营活动单季净收益（大金额）。
        q_investincome: 价值变动单季净收益（大金额）。
        q_dtprofit: 扣除非经常损益后单季净利润（大金额）。
        q_eps: 每股收益(单季度)。
        q_netprofit_margin: 销售净利率(单季度)。
        q_gsprofit_margin: 销售毛利率(单季度)。
        q_exp_to_sales: 销售期间费用率(单季度)。
        q_profit_to_gr: 净利润/营业总收入(单季度)。
        q_saleexp_to_gr: 销售费用/营业总收入(单季度)。
        q_adminexp_to_gr: 管理费用/营业总收入(单季度)。
        q_finaexp_to_gr: 财务费用/营业总收入(单季度)。
        q_impai_to_gr_ttm: 资产减值损失/营业总收入(单季度)。
        q_gc_to_gr: 营业总成本/营业总收入(单季度)。
        q_op_to_gr: 营业利润/营业总收入(单季度)。
        q_roe: 净资产收益率(单季度)。
        q_dt_roe: 净资产收益率(扣除非经常损益，单季度)。
        q_npta: 总资产净利润(单季度)。
        q_opincome_to_ebt: 经营活动净收益/利润总额。
        q_investincome_to_ebt: 价值变动净收益/利润总额。
        q_dtprofit_to_profit: 扣除非经常损益后净利润/净利润。
        q_salescash_to_or: 销售收现/营业收入。
        q_ocf_to_sales: 经营现金流/营业收入。
        q_ocf_to_or: 经营现金流/经营净收益。
        update_flag: 更新标识。
        created_at: 创建时间。
        updated_at: 最后更新时间。
    """

    __tablename__ = "stock_financial"
    __table_args__ = (UniqueConstraint("source", "third_code", "end_date", name="uq_stock_financial_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    third_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    eps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    dt_eps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    total_revenue_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    revenue_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    capital_rese_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    surplus_rese_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    undist_profit_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    extra_item: Mapped[float | None] = mapped_column(_N44, nullable=True)
    profit_dedt: Mapped[float | None] = mapped_column(_N46, nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(_N46, nullable=True)
    current_ratio: Mapped[float | None] = mapped_column(_N44, nullable=True)
    quick_ratio: Mapped[float | None] = mapped_column(_N44, nullable=True)
    cash_ratio: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ar_turn: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ca_turn: Mapped[float | None] = mapped_column(_N44, nullable=True)
    fa_turn: Mapped[float | None] = mapped_column(_N44, nullable=True)
    assets_turn: Mapped[float | None] = mapped_column(_N44, nullable=True)
    op_income: Mapped[float | None] = mapped_column(_N46, nullable=True)
    ebit: Mapped[float | None] = mapped_column(_N46, nullable=True)
    ebitda: Mapped[float | None] = mapped_column(_N46, nullable=True)
    fcff: Mapped[float | None] = mapped_column(_N46, nullable=True)
    fcfe: Mapped[float | None] = mapped_column(_N46, nullable=True)
    current_exint: Mapped[float | None] = mapped_column(_N46, nullable=True)
    noncurrent_exint: Mapped[float | None] = mapped_column(_N46, nullable=True)
    interestdebt: Mapped[float | None] = mapped_column(_N46, nullable=True)
    netdebt: Mapped[float | None] = mapped_column(_N46, nullable=True)
    tangible_asset: Mapped[float | None] = mapped_column(_N46, nullable=True)
    working_capital: Mapped[float | None] = mapped_column(_N46, nullable=True)
    networking_capital: Mapped[float | None] = mapped_column(_N46, nullable=True)
    invest_capital: Mapped[float | None] = mapped_column(_N46, nullable=True)
    retained_earnings: Mapped[float | None] = mapped_column(_N46, nullable=True)
    diluted2_eps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    bps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ocfps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    retainedps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    cfps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ebit_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    fcff_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    fcfe_ps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    netprofit_margin: Mapped[float | None] = mapped_column(_N44, nullable=True)
    grossprofit_margin: Mapped[float | None] = mapped_column(_N44, nullable=True)
    cogs_of_sales: Mapped[float | None] = mapped_column(_N44, nullable=True)
    expense_of_sales: Mapped[float | None] = mapped_column(_N44, nullable=True)
    profit_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    saleexp_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    adminexp_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    finaexp_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    impai_ttm: Mapped[float | None] = mapped_column(_N44, nullable=True)
    gc_of_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    op_of_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ebit_of_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roe: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roe_waa: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roe_dt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roa: Mapped[float | None] = mapped_column(_N44, nullable=True)
    npta: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roic: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roe_yearly: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roa2_yearly: Mapped[float | None] = mapped_column(_N44, nullable=True)
    debt_to_assets: Mapped[float | None] = mapped_column(_N44, nullable=True)
    assets_to_eqt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    dp_assets_to_eqt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ca_to_assets: Mapped[float | None] = mapped_column(_N44, nullable=True)
    nca_to_assets: Mapped[float | None] = mapped_column(_N44, nullable=True)
    tbassets_to_totalassets: Mapped[float | None] = mapped_column(_N44, nullable=True)
    int_to_talcap: Mapped[float | None] = mapped_column(_N44, nullable=True)
    eqt_to_talcap: Mapped[float | None] = mapped_column(_N44, nullable=True)
    currentdebt_to_debt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    longdeb_to_debt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ocf_to_shortdebt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ocf_to_interestdebt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    ocf_to_debt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    cash_to_liqdebt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    cash_to_liqdebt_withinterest: Mapped[float | None] = mapped_column(_N44, nullable=True)
    op_to_liqdebt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    op_to_debt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    roic_yearly: Mapped[float | None] = mapped_column(_N44, nullable=True)
    profit_to_op: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_opincome: Mapped[float | None] = mapped_column(_N46, nullable=True)
    q_investincome: Mapped[float | None] = mapped_column(_N46, nullable=True)
    q_dtprofit: Mapped[float | None] = mapped_column(_N46, nullable=True)
    q_eps: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_netprofit_margin: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_gsprofit_margin: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_exp_to_sales: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_profit_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_saleexp_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_adminexp_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_finaexp_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_impai_to_gr_ttm: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_gc_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_op_to_gr: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_roe: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_dt_roe: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_npta: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_opincome_to_ebt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_investincome_to_ebt: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_dtprofit_to_profit: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_salescash_to_or: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_ocf_to_sales: Mapped[float | None] = mapped_column(_N44, nullable=True)
    q_ocf_to_or: Mapped[float | None] = mapped_column(_N44, nullable=True)
    update_flag: Mapped[str | None] = mapped_column(String(4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
