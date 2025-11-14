"""
Tests for Ratio Calculation Service.

Tests cover:
- Liquidity ratios (5 tests)
- Profitability ratios (8 tests)
- Leverage ratios (6 tests)
- Efficiency ratios (9 tests)
- Edge cases (division by zero, None values, negative equity)
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
from app.services.ratio_calculation_service import RatioCalculationService


@pytest.fixture
def tenant_id():
    """Fixture for tenant ID."""
    return str(uuid4())


@pytest.fixture
def company_id():
    """Fixture for company ID."""
    return uuid4()


@pytest.fixture
def sample_income_statement(company_id, tenant_id):
    """Sample income statement for testing."""
    return IncomeStatement(
        id=uuid4(),
        company_id=company_id,
        tenant_id=tenant_id,
        period_end_date=date(2023, 12, 31),
        period_type="Annual",
        fiscal_year=2023,
        fiscal_quarter=4,
        revenue=Decimal("1000000"),
        cost_of_revenue=Decimal("600000"),
        gross_profit=Decimal("400000"),
        operating_expenses=Decimal("200000"),
        operating_income=Decimal("200000"),
        interest_expense=Decimal("20000"),
        income_before_tax=Decimal("180000"),
        income_tax_expense=Decimal("45000"),
        net_income=Decimal("135000"),
        ebitda=Decimal("250000"),
    )


@pytest.fixture
def sample_balance_sheet(company_id, tenant_id):
    """Sample balance sheet for testing."""
    return BalanceSheet(
        id=uuid4(),
        company_id=company_id,
        tenant_id=tenant_id,
        period_end_date=date(2023, 12, 31),
        fiscal_year=2023,
        fiscal_quarter=4,
        # Assets
        cash_and_equivalents=Decimal("100000"),
        accounts_receivable=Decimal("150000"),
        inventory=Decimal("200000"),
        current_assets=Decimal("500000"),
        property_plant_equipment=Decimal("800000"),
        total_assets=Decimal("1500000"),
        # Liabilities
        accounts_payable=Decimal("100000"),
        short_term_debt=Decimal("50000"),
        current_liabilities=Decimal("200000"),
        long_term_debt=Decimal("400000"),
        total_liabilities=Decimal("700000"),
        # Equity
        total_equity=Decimal("800000"),
    )


@pytest.fixture
def sample_cash_flow(company_id, tenant_id):
    """Sample cash flow statement for testing."""
    return CashFlowStatement(
        id=uuid4(),
        company_id=company_id,
        tenant_id=tenant_id,
        period_end_date=date(2023, 12, 31),
        period_type="Annual",
        fiscal_year=2023,
        fiscal_quarter=4,
        net_income=Decimal("135000"),
        operating_cash_flow=Decimal("180000"),
        investing_cash_flow=Decimal("-100000"),
        financing_cash_flow=Decimal("-50000"),
        net_change_in_cash=Decimal("30000"),
    )


class TestSafeDivide:
    """Test safe_divide utility method."""

    def test_normal_division(self):
        """Test normal division."""
        result = RatioCalculationService.safe_divide(Decimal("10"), Decimal("2"))
        assert result == Decimal("5")

    def test_division_by_zero(self):
        """Test division by zero returns None."""
        result = RatioCalculationService.safe_divide(Decimal("10"), Decimal("0"))
        assert result is None

    def test_none_numerator(self):
        """Test None numerator returns None."""
        result = RatioCalculationService.safe_divide(None, Decimal("2"))
        assert result is None

    def test_none_denominator(self):
        """Test None denominator returns None."""
        result = RatioCalculationService.safe_divide(Decimal("10"), None)
        assert result is None


@pytest.mark.asyncio
class TestLiquidityRatios:
    """Test liquidity ratio calculations."""

    async def test_current_ratio(self, test_db: AsyncSession, tenant_id, sample_balance_sheet):
        """Test current ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet)

        # Current Ratio = Current Assets / Current Liabilities = 500000 / 200000 = 2.5
        assert ratios["current_ratio"] == Decimal("2.5")

    async def test_quick_ratio(self, test_db: AsyncSession, tenant_id, sample_balance_sheet):
        """Test quick ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet)

        # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
        # = (500000 - 200000) / 200000 = 1.5
        assert ratios["quick_ratio"] == Decimal("1.5")

    async def test_cash_ratio(self, test_db: AsyncSession, tenant_id, sample_balance_sheet):
        """Test cash ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet)

        # Cash Ratio = Cash & Equivalents / Current Liabilities = 100000 / 200000 = 0.5
        assert ratios["cash_ratio"] == Decimal("0.5")

    async def test_operating_cash_flow_ratio(
        self, test_db: AsyncSession, tenant_id, sample_balance_sheet, sample_cash_flow
    ):
        """Test operating cash flow ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet, sample_cash_flow)

        # Operating CF Ratio = Operating CF / Current Liabilities = 180000 / 200000 = 0.9
        assert ratios["operating_cash_flow_ratio"] == Decimal("0.9")

    async def test_working_capital_ratio(self, test_db: AsyncSession, tenant_id, sample_balance_sheet):
        """Test working capital ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet)

        # Working Capital Ratio = (Current Assets - Current Liabilities) / Total Assets
        # = (500000 - 200000) / 1500000 = 0.2
        assert ratios["working_capital_ratio"] == Decimal("0.2")


@pytest.mark.asyncio
class TestProfitabilityRatios:
    """Test profitability ratio calculations."""

    async def test_gross_margin(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test gross margin calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # Gross Margin = Gross Profit / Revenue = 400000 / 1000000 = 0.4
        assert ratios["gross_margin"] == Decimal("0.4")

    async def test_operating_margin(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test operating margin calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # Operating Margin = Operating Income / Revenue = 200000 / 1000000 = 0.2
        assert ratios["operating_margin"] == Decimal("0.2")

    async def test_net_margin(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test net margin calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # Net Margin = Net Income / Revenue = 135000 / 1000000 = 0.135
        assert ratios["net_margin"] == Decimal("0.135")

    async def test_ebitda_margin(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test EBITDA margin calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # EBITDA Margin = EBITDA / Revenue = 250000 / 1000000 = 0.25
        assert ratios["ebitda_margin"] == Decimal("0.25")

    async def test_roa(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test ROA calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # ROA = Net Income / Total Assets = 135000 / 1500000 = 0.09
        assert ratios["roa"] == Decimal("0.09")

    async def test_roe(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test ROE calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # ROE = Net Income / Total Equity = 135000 / 800000 = 0.16875
        assert ratios["roe"] == Decimal("0.16875")

    async def test_roic(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test ROIC calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # Tax Rate = 45000 / 180000 = 0.25
        # NOPAT = 200000 * (1 - 0.25) = 150000
        # Invested Capital = 800000 + 450000 = 1250000
        # ROIC = 150000 / 1250000 = 0.12
        assert ratios["roic"] == Decimal("0.12")

    async def test_roce(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test ROCE calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # Capital Employed = Total Assets - Current Liabilities = 1500000 - 200000 = 1300000
        # ROCE = Operating Income / Capital Employed = 200000 / 1300000 ≈ 0.153846...
        result = ratios["roce"]
        assert result is not None
        assert abs(result - Decimal("0.153846")) < Decimal("0.001")


@pytest.mark.asyncio
class TestLeverageRatios:
    """Test leverage ratio calculations."""

    async def test_debt_to_equity(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test debt-to-equity calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_leverage_ratios(sample_income_statement, sample_balance_sheet)

        # Total Debt = 50000 + 400000 = 450000
        # Debt-to-Equity = 450000 / 800000 = 0.5625
        assert ratios["debt_to_equity"] == Decimal("0.5625")

    async def test_debt_to_assets(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test debt-to-assets calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_leverage_ratios(sample_income_statement, sample_balance_sheet)

        # Debt-to-Assets = 450000 / 1500000 = 0.3
        assert ratios["debt_to_assets"] == Decimal("0.3")

    async def test_equity_multiplier(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test equity multiplier calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_leverage_ratios(sample_income_statement, sample_balance_sheet)

        # Equity Multiplier = Total Assets / Total Equity = 1500000 / 800000 = 1.875
        assert ratios["equity_multiplier"] == Decimal("1.875")

    async def test_interest_coverage(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test interest coverage calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_leverage_ratios(sample_income_statement, sample_balance_sheet)

        # Interest Coverage = Operating Income / Interest Expense = 200000 / 20000 = 10
        assert ratios["interest_coverage"] == Decimal("10")

    async def test_debt_service_coverage(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test debt service coverage calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_leverage_ratios(sample_income_statement, sample_balance_sheet)

        # Debt Service Coverage = Operating Income / Interest Expense = 200000 / 20000 = 10
        assert ratios["debt_service_coverage"] == Decimal("10")

    async def test_net_debt_to_ebitda(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test net debt to EBITDA calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_leverage_ratios(sample_income_statement, sample_balance_sheet)

        # Net Debt = Total Debt - Cash = 450000 - 100000 = 350000
        # Net Debt / EBITDA = 350000 / 250000 = 1.4
        assert ratios["net_debt_to_ebitda"] == Decimal("1.4")


@pytest.mark.asyncio
class TestEfficiencyRatios:
    """Test efficiency ratio calculations."""

    async def test_asset_turnover(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test asset turnover calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_efficiency_ratios(sample_income_statement, sample_balance_sheet)

        # Asset Turnover = Revenue / Total Assets = 1000000 / 1500000 ≈ 0.666666...
        result = ratios["asset_turnover"]
        assert result is not None
        assert abs(result - Decimal("0.666666")) < Decimal("0.001")

    async def test_inventory_turnover(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test inventory turnover calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_efficiency_ratios(sample_income_statement, sample_balance_sheet)

        # Inventory Turnover = COGS / Inventory = 600000 / 200000 = 3
        assert ratios["inventory_turnover"] == Decimal("3")

    async def test_receivables_turnover(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test receivables turnover calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_efficiency_ratios(sample_income_statement, sample_balance_sheet)

        # Receivables Turnover = Revenue / Receivables = 1000000 / 150000 ≈ 6.666666...
        result = ratios["receivables_turnover"]
        assert result is not None
        assert abs(result - Decimal("6.666666")) < Decimal("0.001")

    async def test_days_sales_outstanding(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test days sales outstanding calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_efficiency_ratios(sample_income_statement, sample_balance_sheet)

        # DSO = 365 / Receivables Turnover = 365 / 6.666... ≈ 54.75
        result = ratios["days_sales_outstanding"]
        assert result is not None
        assert abs(result - Decimal("54.75")) < Decimal("0.1")

    async def test_days_inventory_outstanding(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test days inventory outstanding calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_efficiency_ratios(sample_income_statement, sample_balance_sheet)

        # DIO = 365 / Inventory Turnover = 365 / 3 ≈ 121.666...
        result = ratios["days_inventory_outstanding"]
        assert result is not None
        assert abs(result - Decimal("121.666")) < Decimal("0.1")

    async def test_cash_conversion_cycle(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test cash conversion cycle calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_efficiency_ratios(sample_income_statement, sample_balance_sheet)

        # CCC = DSO + DIO - DPO
        result = ratios["cash_conversion_cycle"]
        assert result is not None
        # Should be positive since we're collecting cash slower than paying suppliers


@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_zero_current_liabilities(self, test_db: AsyncSession, tenant_id, sample_balance_sheet):
        """Test ratios when current liabilities are zero."""
        sample_balance_sheet.current_liabilities = Decimal("0")
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet)

        # Should return None for ratios with zero denominator
        assert ratios["current_ratio"] is None
        assert ratios["quick_ratio"] is None
        assert ratios["cash_ratio"] is None

    async def test_negative_equity(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test ROE when equity is negative."""
        sample_balance_sheet.total_equity = Decimal("-100000")
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_profitability_ratios(sample_income_statement, sample_balance_sheet)

        # Should still calculate ROE with negative equity
        assert ratios["roe"] == Decimal("-1.35")

    async def test_missing_inventory(self, test_db: AsyncSession, tenant_id, sample_balance_sheet):
        """Test quick ratio when inventory is None."""
        sample_balance_sheet.inventory = None
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet)

        # Quick ratio should equal current ratio when inventory is None
        assert ratios["quick_ratio"] == ratios["current_ratio"]

    async def test_missing_cash_flow(self, test_db: AsyncSession, tenant_id, sample_balance_sheet):
        """Test operating cash flow ratio when cash flow is None."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_liquidity_ratios(sample_balance_sheet, None)

        # Operating cash flow ratio should be None
        assert ratios["operating_cash_flow_ratio"] is None


@pytest.mark.asyncio
class TestMarketValueRatios:
    """Test market value ratio calculations."""

    async def test_pe_ratio(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test P/E ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        market_price = Decimal("50")  # $50 per share
        shares = Decimal("10000")  # 10,000 shares
        market_cap = market_price * shares  # $500,000

        ratios = await service.calculate_market_value_ratios(
            sample_income_statement,
            sample_balance_sheet,
            market_price=market_price,
            market_cap=market_cap,
            shares_outstanding=shares,
        )

        # EPS = Net Income / Shares = 135000 / 10000 = 13.5
        # P/E = Market Price / EPS = 50 / 13.5 ≈ 3.7037
        result = ratios["pe_ratio"]
        assert result is not None
        assert abs(result - Decimal("3.7037")) < Decimal("0.001")

    async def test_pb_ratio(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test P/B ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        market_price = Decimal("50")
        shares = Decimal("10000")
        market_cap = market_price * shares

        ratios = await service.calculate_market_value_ratios(
            sample_income_statement,
            sample_balance_sheet,
            market_price=market_price,
            market_cap=market_cap,
            shares_outstanding=shares,
        )

        # Book Value per Share = Total Equity / Shares = 800000 / 10000 = 80
        # P/B = Market Price / Book Value per Share = 50 / 80 = 0.625
        assert ratios["pb_ratio"] == Decimal("0.625")

    async def test_ps_ratio(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test P/S ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        market_price = Decimal("50")
        shares = Decimal("10000")
        market_cap = market_price * shares  # 500,000

        ratios = await service.calculate_market_value_ratios(
            sample_income_statement,
            sample_balance_sheet,
            market_price=market_price,
            market_cap=market_cap,
            shares_outstanding=shares,
        )

        # P/S = Market Cap / Revenue = 500000 / 1000000 = 0.5
        assert ratios["ps_ratio"] == Decimal("0.5")

    async def test_ev_to_ebitda(
        self, test_db: AsyncSession, tenant_id, sample_income_statement, sample_balance_sheet
    ):
        """Test EV/EBITDA calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        market_price = Decimal("50")
        shares = Decimal("10000")
        market_cap = market_price * shares  # 500,000

        ratios = await service.calculate_market_value_ratios(
            sample_income_statement,
            sample_balance_sheet,
            market_price=market_price,
            market_cap=market_cap,
            shares_outstanding=shares,
        )

        # Total Debt = 450,000 (50k short + 400k long)
        # EV = Market Cap + Debt - Cash = 500000 + 450000 - 100000 = 850,000
        # EV/EBITDA = 850000 / 250000 = 3.4
        assert ratios["ev_to_ebitda"] == Decimal("3.4")


@pytest.mark.asyncio
class TestGrowthRatios:
    """Test growth ratio calculations."""

    @pytest.fixture
    def prev_income_statement(self, company_id, tenant_id):
        """Previous period income statement for YoY comparison."""
        return IncomeStatement(
            id=uuid4(),
            company_id=company_id,
            tenant_id=tenant_id,
            period_end_date=date(2022, 12, 31),
            period_type="Annual",
            fiscal_year=2022,
            fiscal_quarter=4,
            revenue=Decimal("800000"),  # 25% growth to 1M
            net_income=Decimal("100000"),  # 35% growth to 135k
            ebitda=Decimal("200000"),  # 25% growth to 250k
        )

    @pytest.fixture
    def prev_balance_sheet(self, company_id, tenant_id):
        """Previous period balance sheet for YoY comparison."""
        return BalanceSheet(
            id=uuid4(),
            company_id=company_id,
            tenant_id=tenant_id,
            period_end_date=date(2022, 12, 31),
            period_type="Annual",
            fiscal_year=2022,
            fiscal_quarter=4,
            total_assets=Decimal("1200000"),  # 25% growth to 1.5M
            total_equity=Decimal("700000"),
            total_liabilities=Decimal("500000"),
        )

    async def test_revenue_growth(
        self,
        test_db: AsyncSession,
        tenant_id,
        sample_income_statement,
        prev_income_statement,
    ):
        """Test revenue growth YoY calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_growth_ratios(
            sample_income_statement, prev_income_statement
        )

        # Revenue Growth = (1000000 - 800000) / 800000 = 0.25 (25%)
        assert ratios["revenue_growth_yoy"] == Decimal("0.25")

    async def test_net_income_growth(
        self,
        test_db: AsyncSession,
        tenant_id,
        sample_income_statement,
        prev_income_statement,
    ):
        """Test net income growth YoY calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_growth_ratios(
            sample_income_statement, prev_income_statement
        )

        # NI Growth = (135000 - 100000) / 100000 = 0.35 (35%)
        assert ratios["net_income_growth_yoy"] == Decimal("0.35")

    async def test_ebitda_growth(
        self,
        test_db: AsyncSession,
        tenant_id,
        sample_income_statement,
        prev_income_statement,
    ):
        """Test EBITDA growth YoY calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_growth_ratios(
            sample_income_statement, prev_income_statement
        )

        # EBITDA Growth = (250000 - 200000) / 200000 = 0.25 (25%)
        assert ratios["ebitda_growth_yoy"] == Decimal("0.25")

    async def test_assets_growth(
        self,
        test_db: AsyncSession,
        tenant_id,
        sample_income_statement,
        prev_income_statement,
        sample_balance_sheet,
        prev_balance_sheet,
    ):
        """Test total assets growth YoY calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_growth_ratios(
            sample_income_statement,
            prev_income_statement,
            sample_balance_sheet,
            prev_balance_sheet,
        )

        # Assets Growth = (1500000 - 1200000) / 1200000 = 0.25 (25%)
        assert ratios["total_assets_growth_yoy"] == Decimal("0.25")


@pytest.mark.asyncio
class TestCashFlowRatios:
    """Test cash flow ratio calculations."""

    async def test_operating_cf_margin(
        self,
        test_db: AsyncSession,
        tenant_id,
        sample_income_statement,
        sample_cash_flow,
        sample_balance_sheet,
    ):
        """Test operating cash flow margin calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_cash_flow_ratios(
            sample_income_statement, sample_cash_flow, sample_balance_sheet
        )

        # Operating CF Margin = Operating CF / Revenue = 180000 / 1000000 = 0.18
        assert ratios["operating_cf_margin"] == Decimal("0.18")

    async def test_fcf_to_net_income(
        self,
        test_db: AsyncSession,
        tenant_id,
        sample_income_statement,
        sample_cash_flow,
        sample_balance_sheet,
    ):
        """Test FCF to net income ratio calculation."""
        # Add capital expenditures to calculate FCF
        sample_cash_flow.capital_expenditures = Decimal("-50000")  # Negative value

        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_cash_flow_ratios(
            sample_income_statement, sample_cash_flow, sample_balance_sheet
        )

        # FCF = Operating CF + CapEx = 180000 + (-50000) = 130000
        # FCF to NI = 130000 / 135000 ≈ 0.962963
        result = ratios["fcf_to_net_income"]
        assert result is not None
        assert abs(result - Decimal("0.962963")) < Decimal("0.001")

    async def test_cash_flow_coverage(
        self,
        test_db: AsyncSession,
        tenant_id,
        sample_income_statement,
        sample_cash_flow,
        sample_balance_sheet,
    ):
        """Test cash flow coverage ratio calculation."""
        service = RatioCalculationService(test_db, tenant_id)
        ratios = await service.calculate_cash_flow_ratios(
            sample_income_statement, sample_cash_flow, sample_balance_sheet
        )

        # Total Debt = 450,000
        # Cash Flow Coverage = Operating CF / Total Debt = 180000 / 450000 = 0.4
        assert ratios["cash_flow_coverage"] == Decimal("0.4")
