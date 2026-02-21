"""股票财务指标领域实体。"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.shared_kernel.domain.entity import Entity

from ..value_objects.data_source import DataSource


@dataclass(eq=False)
class StockFinancial(Entity[int | None]):
    """股票财务指标实体。逻辑唯一键：(source, third_code, end_date)。仅含业务属性。

    Attributes:
        id: 主键；新建未持久化时为 None。
        source: 数据来源（如 Tushare）。
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
        profit_dedt: 扣除非经常性损益后净利润。
        gross_margin: 毛利润。
        current_ratio: 流动比率。
        quick_ratio: 速动比率。
        cash_ratio: 保守速动比率。
        ar_turn: 应收账款周转率。
        ca_turn: 流动资产周转率。
        fa_turn: 固定资产周转率。
        assets_turn: 总资产周转率。
        op_income: 经营活动净收益。
        ebit: 息税前利润。
        ebitda: 息税折旧摊销前利润。
        fcff: 企业自由现金流量。
        fcfe: 股权自由现金流量。
        current_exint: 无息流动负债。
        noncurrent_exint: 无息非流动负债。
        interestdebt: 带息债务。
        netdebt: 净债务。
        tangible_asset: 有形资产。
        working_capital: 营运资金。
        networking_capital: 营运流动资本。
        invest_capital: 全部投入资本。
        retained_earnings: 留存收益。
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
        eqt_to_talcap: 归属于母公司的股东权益/全部投入资本。
        currentdebt_to_debt: 流动负债/负债合计。
        longdeb_to_debt: 非流动负债/负债合计。
        ocf_to_shortdebt: 经营活动产生的现金流量净额/流动负债。
        ocf_to_interestdebt: 经营活动产生的现金流量净额/带息债务。
        ocf_to_debt: 经营活动产生的现金流量净额/负债合计。
        cash_to_liqdebt: 货币资金/流动负债。
        cash_to_liqdebt_withinterest: 货币资金/带息流动负债。
        op_to_liqdebt: 经营活动产生的现金流量净额/流动负债。
        op_to_debt: 经营活动产生的现金流量净额/负债合计。
        roic_yearly: 年化投入资本回报率。
        profit_to_op: 净利润/经营活动净收益。
        q_opincome: 经营活动单季净收益。
        q_investincome: 价值变动单季净收益。
        q_dtprofit: 扣除非经常损益后单季净利润。
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
        q_salescash_to_or: 销售商品提供劳务收到的现金/营业收入。
        q_ocf_to_sales: 经营活动产生的现金流量净额/营业收入。
        q_ocf_to_or: 经营活动产生的现金流量净额/经营活动净收益。
        update_flag: 更新标识。
    """

    id: int | None
    source: DataSource
    third_code: str
    symbol: str | None
    ann_date: date | None
    end_date: date
    eps: Decimal | None
    dt_eps: Decimal | None
    total_revenue_ps: Decimal | None
    revenue_ps: Decimal | None
    capital_rese_ps: Decimal | None
    surplus_rese_ps: Decimal | None
    undist_profit_ps: Decimal | None
    extra_item: Decimal | None
    profit_dedt: Decimal | None
    gross_margin: Decimal | None
    current_ratio: Decimal | None
    quick_ratio: Decimal | None
    cash_ratio: Decimal | None
    ar_turn: Decimal | None
    ca_turn: Decimal | None
    fa_turn: Decimal | None
    assets_turn: Decimal | None
    op_income: Decimal | None
    ebit: Decimal | None
    ebitda: Decimal | None
    fcff: Decimal | None
    fcfe: Decimal | None
    current_exint: Decimal | None
    noncurrent_exint: Decimal | None
    interestdebt: Decimal | None
    netdebt: Decimal | None
    tangible_asset: Decimal | None
    working_capital: Decimal | None
    networking_capital: Decimal | None
    invest_capital: Decimal | None
    retained_earnings: Decimal | None
    diluted2_eps: Decimal | None
    bps: Decimal | None
    ocfps: Decimal | None
    retainedps: Decimal | None
    cfps: Decimal | None
    ebit_ps: Decimal | None
    fcff_ps: Decimal | None
    fcfe_ps: Decimal | None
    netprofit_margin: Decimal | None
    grossprofit_margin: Decimal | None
    cogs_of_sales: Decimal | None
    expense_of_sales: Decimal | None
    profit_to_gr: Decimal | None
    saleexp_to_gr: Decimal | None
    adminexp_to_gr: Decimal | None
    finaexp_to_gr: Decimal | None
    impai_ttm: Decimal | None
    gc_of_gr: Decimal | None
    op_of_gr: Decimal | None
    ebit_of_gr: Decimal | None
    roe: Decimal | None
    roe_waa: Decimal | None
    roe_dt: Decimal | None
    roa: Decimal | None
    npta: Decimal | None
    roic: Decimal | None
    roe_yearly: Decimal | None
    roa2_yearly: Decimal | None
    debt_to_assets: Decimal | None
    assets_to_eqt: Decimal | None
    dp_assets_to_eqt: Decimal | None
    ca_to_assets: Decimal | None
    nca_to_assets: Decimal | None
    tbassets_to_totalassets: Decimal | None
    int_to_talcap: Decimal | None
    eqt_to_talcap: Decimal | None
    currentdebt_to_debt: Decimal | None
    longdeb_to_debt: Decimal | None
    ocf_to_shortdebt: Decimal | None
    ocf_to_interestdebt: Decimal | None
    ocf_to_debt: Decimal | None
    cash_to_liqdebt: Decimal | None
    cash_to_liqdebt_withinterest: Decimal | None
    op_to_liqdebt: Decimal | None
    op_to_debt: Decimal | None
    roic_yearly: Decimal | None
    profit_to_op: Decimal | None
    q_opincome: Decimal | None
    q_investincome: Decimal | None
    q_dtprofit: Decimal | None
    q_eps: Decimal | None
    q_netprofit_margin: Decimal | None
    q_gsprofit_margin: Decimal | None
    q_exp_to_sales: Decimal | None
    q_profit_to_gr: Decimal | None
    q_saleexp_to_gr: Decimal | None
    q_adminexp_to_gr: Decimal | None
    q_finaexp_to_gr: Decimal | None
    q_impai_to_gr_ttm: Decimal | None
    q_gc_to_gr: Decimal | None
    q_op_to_gr: Decimal | None
    q_roe: Decimal | None
    q_dt_roe: Decimal | None
    q_npta: Decimal | None
    q_opincome_to_ebt: Decimal | None
    q_investincome_to_ebt: Decimal | None
    q_dtprofit_to_profit: Decimal | None
    q_salescash_to_or: Decimal | None
    q_ocf_to_sales: Decimal | None
    q_ocf_to_or: Decimal | None
    update_flag: str | None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StockFinancial):
            return False
        if self.id is None or other.id is None:
            return self is other
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))
