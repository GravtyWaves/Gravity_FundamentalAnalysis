"""
Unit tests for ValueDriversService.

Tests value driver analysis methods:
- DuPont analysis (3-level ROE decomposition)
- Revenue drivers (CAGR, growth analysis)
- Margin drivers (gross to net waterfall)
- Capital efficiency drivers (asset turnover, working capital)
- Waterfall analysis (period-over-period changes)
"""
# pyright: reportArgumentType=false


import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.value_drivers_service import ValueDriversService
from app.models.company import Company
from app.models.financial_statements import IncomeStatement, BalanceSheet


@pytest.fixture
async def company(test_db: AsyncSession, test_tenant_id: str) -> Company:
    """Create a test company."""
    company = Company(
        id=uuid4(),
        ticker="VD",
        name_en="Value Drivers Test Company",
        name_fa="شرکت تست محرک ارزش",
        sector_en="Technology",
        sector_fa="فناوری",
        industry_en="Software",
        industry_fa="نرم‌افزار",
        tenant_id=test_tenant_id,
        is_active=True
    )
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    return company


@pytest.fixture
async def income_statement(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> IncomeStatement:
    """Create a test income statement."""
    stmt = IncomeStatement(
        id=uuid4(),
        company_id=company.id,
        period_end_date=date(2023, 12, 31),
        fiscal_year=2023,
        fiscal_period="FY",
        total_revenue=Decimal("10000000"),  # $10M revenue
        cost_of_revenue=Decimal("6000000"),  # $6M COGS
        gross_profit=Decimal("4000000"),  # $4M gross profit
        operating_expenses=Decimal("2000000"),  # $2M OpEx
        operating_income=Decimal("2000000"),  # $2M EBIT
        net_income=Decimal("1500000"),  # $1.5M net income
        ebitda=Decimal("2500000"),  # $2.5M EBITDA
        tenant_id=test_tenant_id
    )
    test_db.add(stmt)
    await test_db.commit()
    await test_db.refresh(stmt)
    return stmt


@pytest.fixture
async def balance_sheet(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> BalanceSheet:
    """Create a test balance sheet."""
    sheet = BalanceSheet(
        id=uuid4(),
        company_id=company.id,
        period_end_date=date(2023, 12, 31),
        fiscal_year=2023,
        fiscal_period="FY",
        total_assets=Decimal("50000000"),  # $50M assets
        total_current_assets=Decimal("20000000"),  # $20M current assets
        total_non_current_assets=Decimal("30000000"),
        property_plant_equipment=Decimal("25000000"),  # $25M PPE
        total_liabilities=Decimal("20000000"),  # $20M liabilities
        total_current_liabilities=Decimal("8000000"),  # $8M current liabilities
        total_non_current_liabilities=Decimal("12000000"),
        total_equity=Decimal("30000000"),  # $30M equity
        retained_earnings=Decimal("15000000"),
        tenant_id=test_tenant_id
    )
    test_db.add(sheet)
    await test_db.commit()
    await test_db.refresh(sheet)
    return sheet


@pytest.fixture
async def historical_income_statements(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> list[IncomeStatement]:
    """Create 5 years of historical income statements."""
    statements = []
    base_revenue = 8000000  # Start at $8M
    
    for year in range(2019, 2024):
        revenue = base_revenue * (1.15 ** (year - 2019))  # 15% annual growth
        
        stmt = IncomeStatement(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(year, 12, 31),
            fiscal_year=year,
            fiscal_period="FY",
            total_revenue=Decimal(str(int(revenue))),
            cost_of_revenue=Decimal(str(int(revenue * 0.60))),
            gross_profit=Decimal(str(int(revenue * 0.40))),
            operating_expenses=Decimal(str(int(revenue * 0.20))),
            operating_income=Decimal(str(int(revenue * 0.20))),
            net_income=Decimal(str(int(revenue * 0.15))),
            ebitda=Decimal(str(int(revenue * 0.25))),
            tenant_id=test_tenant_id
        )
        test_db.add(stmt)
        statements.append(stmt)
    
    await test_db.commit()
    for stmt in statements:
        await test_db.refresh(stmt)
    
    return statements


@pytest.fixture
def value_drivers_service(test_db: AsyncSession, test_tenant_id: str) -> ValueDriversService:
    """Create value drivers service instance."""
    return ValueDriversService(db=test_db, tenant_id=test_tenant_id)


@pytest.mark.asyncio
class TestDuPontAnalysis:
    """Test DuPont ROE decomposition."""

    async def test_dupont_three_level(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test 3-level DuPont analysis."""
        result = await value_drivers_service.dupont_analysis(company.id)
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "dupont"
        assert "three_level_dupont" in result
        
        # Verify components
        dupont = result["three_level_dupont"]
        assert "roe" in dupont
        assert "components" in dupont
        
        components = dupont["components"]
        assert "net_profit_margin" in components
        assert "asset_turnover" in components
        assert "equity_multiplier" in components

    async def test_dupont_roe_calculation(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test ROE calculation accuracy."""
        result = await value_drivers_service.dupont_analysis(company.id)
        
        dupont = result["three_level_dupont"]
        components = dupont["components"]
        
        # Manually calculate ROE
        npm = components["net_profit_margin"]
        at = components["asset_turnover"]
        em = components["equity_multiplier"]
        calculated_roe = npm * at * em
        
        # Should match reported ROE
        assert abs(dupont["roe"] - calculated_roe) < 0.001

    async def test_dupont_profit_margin(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test net profit margin calculation."""
        result = await value_drivers_service.dupont_analysis(company.id)
        
        # Net profit margin = Net Income / Revenue
        # $1.5M / $10M = 0.15 = 15%
        npm = result["three_level_dupont"]["components"]["net_profit_margin"]
        assert abs(npm - 0.15) < 0.01

    async def test_dupont_asset_turnover(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test asset turnover calculation."""
        result = await value_drivers_service.dupont_analysis(company.id)
        
        # Asset turnover = Revenue / Total Assets
        # $10M / $50M = 0.20
        at = result["three_level_dupont"]["components"]["asset_turnover"]
        assert abs(at - 0.20) < 0.01

    async def test_dupont_equity_multiplier(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test equity multiplier calculation."""
        result = await value_drivers_service.dupont_analysis(company.id)
        
        # Equity multiplier = Total Assets / Total Equity
        # $50M / $30M = 1.667
        em = result["three_level_dupont"]["components"]["equity_multiplier"]
        assert abs(em - 1.667) < 0.01

    async def test_dupont_interpretation(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test DuPont interpretation of drivers."""
        result = await value_drivers_service.dupont_analysis(company.id)
        
        interpretation = result["three_level_dupont"]["interpretation"]
        
        # Verify interpretation fields exist
        assert "profitability_driver" in interpretation
        assert "efficiency_driver" in interpretation
        assert "leverage_driver" in interpretation

    async def test_dupont_missing_data(
        self,
        value_drivers_service: ValueDriversService,
        company: Company
    ):
        """Test DuPont with missing financial data."""
        # No income statement for company
        with pytest.raises(ValueError, match="No income statement found"):
            await value_drivers_service.dupont_analysis(company.id)


@pytest.mark.asyncio
class TestRevenueDrivers:
    """Test revenue driver analysis."""

    async def test_revenue_drivers_basic(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        historical_income_statements: list[IncomeStatement]
    ):
        """Test basic revenue drivers analysis."""
        result = await value_drivers_service.revenue_drivers(
            company.id,
            num_periods=5
        )
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "revenue_drivers"
        assert "revenue_cagr_pct" in result
        assert "period_analysis" in result

    async def test_revenue_cagr_calculation(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        historical_income_statements: list[IncomeStatement]
    ):
        """Test CAGR calculation."""
        result = await value_drivers_service.revenue_drivers(
            company.id,
            num_periods=5
        )
        
        # With 15% annual growth, CAGR should be ~15%
        cagr = result["revenue_cagr_pct"]
        assert 14 <= cagr <= 16  # Allow small rounding tolerance

    async def test_revenue_period_growth(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        historical_income_statements: list[IncomeStatement]
    ):
        """Test period-over-period revenue growth."""
        result = await value_drivers_service.revenue_drivers(
            company.id,
            num_periods=5
        )
        
        period_analysis = result["period_analysis"]
        
        # Verify each period has required fields
        for period in period_analysis:
            assert "period" in period
            assert "revenue" in period
            assert "previous_revenue" in period
            assert "revenue_growth_pct" in period
            assert "revenue_change" in period

    async def test_revenue_insufficient_data(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement
    ):
        """Test revenue drivers with insufficient data."""
        # Only 1 period available
        with pytest.raises(ValueError, match="Need at least 2 periods"):
            await value_drivers_service.revenue_drivers(company.id)


@pytest.mark.asyncio
class TestMarginDrivers:
    """Test margin driver analysis."""

    async def test_margin_drivers_basic(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        historical_income_statements: list[IncomeStatement]
    ):
        """Test basic margin drivers analysis."""
        result = await value_drivers_service.margin_drivers(
            company.id,
            num_periods=5
        )
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "margin_drivers"
        assert "margin_trends" in result

    async def test_margin_levels(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        historical_income_statements: list[IncomeStatement]
    ):
        """Test margin level calculations (gross, operating, net)."""
        result = await value_drivers_service.margin_drivers(
            company.id,
            num_periods=5
        )
        
        margin_trends = result["margin_trends"]
        
        # Each period should have all margin levels
        for period in margin_trends:
            assert "gross_margin_pct" in period
            assert "operating_margin_pct" in period
            assert "net_margin_pct" in period
            
            # Margins should cascade: Gross > Operating > Net
            assert period["gross_margin_pct"] >= period["operating_margin_pct"]
            assert period["operating_margin_pct"] >= period["net_margin_pct"]

    async def test_margin_compression(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        historical_income_statements: list[IncomeStatement]
    ):
        """Test margin compression analysis."""
        result = await value_drivers_service.margin_drivers(
            company.id,
            num_periods=5
        )
        
        margin_trends = result["margin_trends"]
        
        # Each period should have compression breakdown
        for period in margin_trends:
            compression = period["margin_compression"]
            assert "gross_to_operating" in compression
            assert "operating_to_net" in compression
            assert "total_compression" in compression
            
            # Total compression should equal sum of components
            total = compression["total_compression"]
            parts = compression["gross_to_operating"] + compression["operating_to_net"]
            assert abs(total - parts) < 0.1

    async def test_margin_consistency(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        historical_income_statements: list[IncomeStatement]
    ):
        """Test margin consistency across periods."""
        result = await value_drivers_service.margin_drivers(
            company.id,
            num_periods=5
        )
        
        margin_trends = result["margin_trends"]
        
        # With consistent cost structure (60% COGS, 20% OpEx),
        # margins should be stable
        for period in margin_trends:
            # Gross margin ~40%
            assert 38 <= period["gross_margin_pct"] <= 42
            # Operating margin ~20%
            assert 18 <= period["operating_margin_pct"] <= 22
            # Net margin ~15%
            assert 13 <= period["net_margin_pct"] <= 17


@pytest.mark.asyncio
class TestCapitalEfficiency:
    """Test capital efficiency driver analysis."""

    async def test_capital_efficiency_basic(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test basic capital efficiency analysis."""
        result = await value_drivers_service.capital_efficiency_drivers(company.id)
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "capital_efficiency"
        assert "efficiency_metrics" in result

    async def test_asset_turnover(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test asset turnover calculation."""
        result = await value_drivers_service.capital_efficiency_drivers(company.id)
        
        # Asset turnover = Revenue / Total Assets
        # $10M / $50M = 0.20
        at = result["efficiency_metrics"]["asset_turnover"]
        assert abs(at - 0.20) < 0.01

    async def test_fixed_asset_turnover(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test fixed asset turnover calculation."""
        result = await value_drivers_service.capital_efficiency_drivers(company.id)
        
        # Fixed asset turnover = Revenue / PPE
        # $10M / $25M = 0.40
        fat = result["efficiency_metrics"]["fixed_asset_turnover"]
        assert abs(fat - 0.40) < 0.01

    async def test_working_capital_turnover(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test working capital turnover calculation."""
        result = await value_drivers_service.capital_efficiency_drivers(company.id)
        
        # Working capital = Current Assets - Current Liabilities
        # $20M - $8M = $12M
        # WC Turnover = Revenue / WC = $10M / $12M = 0.833
        wct = result["efficiency_metrics"]["working_capital_turnover"]
        assert abs(wct - 0.833) < 0.01

    async def test_efficiency_interpretation(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test efficiency metric interpretation."""
        result = await value_drivers_service.capital_efficiency_drivers(company.id)
        
        interpretation = result["interpretation"]
        
        # Verify interpretation fields
        assert "asset_efficiency" in interpretation
        assert "fixed_asset_utilization" in interpretation
        assert "working_capital_management" in interpretation


@pytest.mark.asyncio
class TestWaterfallAnalysis:
    """Test waterfall analysis."""

    async def test_waterfall_net_income(
        self,
        test_db: AsyncSession,
        value_drivers_service: ValueDriversService,
        company: Company,
        test_tenant_id: str
    ):
        """Test net income waterfall analysis."""
        # Create two periods
        stmt1 = IncomeStatement(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(2022, 12, 31),
            fiscal_year=2022,
            fiscal_period="FY",
            total_revenue=Decimal("8000000"),
            cost_of_revenue=Decimal("5000000"),
            gross_profit=Decimal("3000000"),
            operating_expenses=Decimal("1500000"),
            operating_income=Decimal("1500000"),
            net_income=Decimal("1000000"),
            tenant_id=test_tenant_id
        )
        test_db.add(stmt1)
        
        stmt2 = IncomeStatement(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(2023, 12, 31),
            fiscal_year=2023,
            fiscal_period="FY",
            total_revenue=Decimal("10000000"),
            cost_of_revenue=Decimal("6000000"),
            gross_profit=Decimal("4000000"),
            operating_expenses=Decimal("2000000"),
            operating_income=Decimal("2000000"),
            net_income=Decimal("1500000"),
            tenant_id=test_tenant_id
        )
        test_db.add(stmt2)
        await test_db.commit()
        
        result = await value_drivers_service.waterfall_analysis(
            company.id,
            metric="net_income"
        )
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "waterfall"
        assert result["metric"] == "net_income"
        
        # Verify total change
        # $1.5M - $1M = $0.5M = 50% increase
        assert result["total_change"] == 500000
        assert result["change_pct"] == 50.0

    async def test_waterfall_revenue(
        self,
        test_db: AsyncSession,
        value_drivers_service: ValueDriversService,
        company: Company,
        test_tenant_id: str
    ):
        """Test revenue waterfall analysis."""
        # Create two periods
        stmt1 = IncomeStatement(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(2022, 12, 31),
            fiscal_year=2022,
            fiscal_period="FY",
            total_revenue=Decimal("8000000"),
            tenant_id=test_tenant_id
        )
        test_db.add(stmt1)
        
        stmt2 = IncomeStatement(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(2023, 12, 31),
            fiscal_year=2023,
            fiscal_period="FY",
            total_revenue=Decimal("10000000"),
            tenant_id=test_tenant_id
        )
        test_db.add(stmt2)
        await test_db.commit()
        
        result = await value_drivers_service.waterfall_analysis(
            company.id,
            metric="revenue"
        )
        
        # Verify structure
        assert result["metric"] == "revenue"
        assert "waterfall_components" in result

    async def test_waterfall_insufficient_periods(
        self,
        value_drivers_service: ValueDriversService,
        company: Company,
        income_statement: IncomeStatement
    ):
        """Test waterfall with insufficient periods."""
        # Only 1 period
        with pytest.raises(ValueError, match="Need at least 2 periods"):
            await value_drivers_service.waterfall_analysis(company.id)

    async def test_waterfall_invalid_metric(
        self,
        test_db: AsyncSession,
        value_drivers_service: ValueDriversService,
        company: Company,
        test_tenant_id: str
    ):
        """Test waterfall with invalid metric."""
        # Create two periods
        for year in [2022, 2023]:
            stmt = IncomeStatement(
                id=uuid4(),
                company_id=company.id,
                period_end_date=date(year, 12, 31),
                fiscal_year=year,
                fiscal_period="FY",
                total_revenue=Decimal("10000000"),
                tenant_id=test_tenant_id
            )
            test_db.add(stmt)
        await test_db.commit()
        
        with pytest.raises(ValueError, match="Unsupported metric"):
            await value_drivers_service.waterfall_analysis(
                company.id,
                metric="invalid_metric"
            )


@pytest.mark.asyncio
class TestMultiTenancy:
    """Test multi-tenancy isolation."""

    async def test_dupont_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet,
        test_tenant_id: str
    ):
        """Test DuPont analysis respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = ValueDriversService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should not find data from different tenant
        with pytest.raises(ValueError):
            await service_other_tenant.dupont_analysis(company.id)

    async def test_revenue_drivers_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        historical_income_statements: list[IncomeStatement],
        test_tenant_id: str
    ):
        """Test revenue drivers respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = ValueDriversService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should not find data from different tenant
        with pytest.raises(ValueError):
            await service_other_tenant.revenue_drivers(company.id)
