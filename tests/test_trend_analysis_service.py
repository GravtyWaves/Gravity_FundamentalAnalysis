"""
Unit tests for TrendAnalysisService.

Tests revenue trends, profitability trends, ratio trends, CAGR calculations,
linear regression, moving averages, and anomaly detection.
"""

import pytest
from datetime import date
from decimal import Decimal
from typing import List
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.trend_analysis_service import TrendAnalysisService
from app.models.company import Company
from app.models.financial_statements import IncomeStatement, BalanceSheet
from app.models.ratios import FinancialRatio


@pytest.fixture
async def company(test_db: AsyncSession, test_tenant_id: str) -> Company:
    """Create a test company."""
    company = Company(
        id=uuid4(),
        ticker="TEST",
        name_en="Test Company",
        name_fa="شرکت تست",
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
async def income_statements(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> List[IncomeStatement]:
    """Create test income statements for 5 years."""
    statements = []
    revenues = [
        Decimal("1000000"),  # Year 1
        Decimal("1200000"),  # Year 2 (+20%)
        Decimal("1500000"),  # Year 3 (+25%)
        Decimal("1800000"),  # Year 4 (+20%)
        Decimal("2200000"),  # Year 5 (+22%)
    ]
    
    for i, revenue in enumerate(revenues):
        year = 2019 + i
        # Calculate consistent margins
        gross_profit = revenue * Decimal("0.6")  # 60% margin
        operating_income = revenue * Decimal("0.25")  # 25% margin
        net_income = revenue * Decimal("0.15")  # 15% margin
        
        stmt = IncomeStatement(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(year, 12, 31),
            fiscal_year=year,
            fiscal_period="FY",
            revenue=revenue,
            cost_of_revenue=revenue - gross_profit,
            gross_profit=gross_profit,
            operating_expenses=gross_profit - operating_income,
            operating_income=operating_income,
            net_income=net_income,
            ebitda=operating_income * Decimal("1.1"),
            earnings_per_share=net_income / Decimal("1000000"),
            tenant_id=test_tenant_id
        )
        test_db.add(stmt)
        statements.append(stmt)
    
    await test_db.commit()
    for stmt in statements:
        await test_db.refresh(stmt)
    
    return statements


@pytest.fixture
async def balance_sheets(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> List[BalanceSheet]:
    """Create test balance sheets for 5 years."""
    sheets = []
    
    for i in range(5):
        year = 2019 + i
        total_assets = Decimal("5000000") * (Decimal("1.15") ** i)
        total_equity = total_assets * Decimal("0.6")
        total_liabilities = total_assets - total_equity
        
        sheet = BalanceSheet(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(year, 12, 31),
            fiscal_year=year,
            fiscal_period="FY",
            total_assets=total_assets,
            total_current_assets=total_assets * Decimal("0.4"),
            total_non_current_assets=total_assets * Decimal("0.6"),
            total_liabilities=total_liabilities,
            total_current_liabilities=total_liabilities * Decimal("0.5"),
            total_non_current_liabilities=total_liabilities * Decimal("0.5"),
            total_equity=total_equity,
            retained_earnings=total_equity * Decimal("0.7"),
            tenant_id=test_tenant_id
        )
        test_db.add(sheet)
        sheets.append(sheet)
    
    await test_db.commit()
    for sheet in sheets:
        await test_db.refresh(sheet)
    
    return sheets


@pytest.fixture
async def financial_ratios(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> List[FinancialRatio]:
    """Create test financial ratios for 5 years."""
    ratios = []
    
    for i in range(5):
        year = 2019 + i
        ratio = FinancialRatio(
            id=uuid4(),
            company_id=company.id,
            period_end_date=date(year, 12, 31),
            fiscal_year=year,
            fiscal_period="FY",
            # Profitability
            gross_profit_margin=Decimal("0.60"),
            operating_profit_margin=Decimal("0.25"),
            net_profit_margin=Decimal("0.15"),
            return_on_equity=Decimal("0.12") + (Decimal("0.01") * i),
            return_on_assets=Decimal("0.08") + (Decimal("0.005") * i),
            # Liquidity
            current_ratio=Decimal("2.0"),
            quick_ratio=Decimal("1.5"),
            # Leverage
            debt_to_equity=Decimal("0.67"),
            tenant_id=test_tenant_id
        )
        test_db.add(ratio)
        ratios.append(ratio)
    
    await test_db.commit()
    for ratio in ratios:
        await test_db.refresh(ratio)
    
    return ratios


@pytest.fixture
def trend_service(test_db: AsyncSession, test_tenant_id: str) -> TrendAnalysisService:
    """Create trend analysis service instance."""
    return TrendAnalysisService(db=test_db, tenant_id=test_tenant_id)


class TestCAGRCalculation:
    """Test CAGR calculation methods."""

    def test_cagr_positive_growth(self, trend_service: TrendAnalysisService):
        """Test CAGR calculation with positive growth."""
        start = Decimal("1000000")
        end = Decimal("2200000")
        years = 5
        
        cagr = trend_service.calculate_cagr(start, end, years)
        
        # CAGR = (2200000/1000000)^(1/5) - 1 ≈ 0.171 (17.1%)
        assert cagr is not None
        assert Decimal("0.15") < cagr < Decimal("0.20")

    def test_cagr_negative_growth(self, trend_service: TrendAnalysisService):
        """Test CAGR calculation with negative growth."""
        start = Decimal("2000000")
        end = Decimal("1500000")
        years = 3
        
        cagr = trend_service.calculate_cagr(start, end, years)
        
        # Should be negative
        assert cagr is not None
        assert cagr < Decimal("0")

    def test_cagr_zero_start_value(self, trend_service: TrendAnalysisService):
        """Test CAGR with zero start value."""
        cagr = trend_service.calculate_cagr(Decimal("0"), Decimal("1000"), 5)
        
        # Should return None or handle gracefully
        assert cagr is None

    def test_cagr_one_year(self, trend_service: TrendAnalysisService):
        """Test CAGR with single year."""
        cagr = trend_service.calculate_cagr(
            Decimal("1000"),
            Decimal("1200"),
            1
        )
        
        # Should be 20%
        assert cagr == Decimal("0.20")


class TestYoYGrowthCalculation:
    """Test year-over-year growth calculation."""

    def test_yoy_growth_positive(self, trend_service: TrendAnalysisService):
        """Test YoY growth with positive growth."""
        prev = Decimal("1000000")
        current = Decimal("1200000")
        
        growth = trend_service.calculate_yoy_growth(prev, current)
        
        # (1200000 - 1000000) / 1000000 = 0.20 (20%)
        assert growth == Decimal("0.20")

    def test_yoy_growth_negative(self, trend_service: TrendAnalysisService):
        """Test YoY growth with negative growth."""
        prev = Decimal("1500000")
        current = Decimal("1200000")
        
        growth = trend_service.calculate_yoy_growth(prev, current)
        
        # (1200000 - 1500000) / 1500000 = -0.20 (-20%)
        assert growth == Decimal("-0.20")

    def test_yoy_growth_zero_previous(self, trend_service: TrendAnalysisService):
        """Test YoY growth with zero previous value."""
        growth = trend_service.calculate_yoy_growth(Decimal("0"), Decimal("1000"))
        
        assert growth is None


@pytest.mark.asyncio
class TestRevenueTrendAnalysis:
    """Test revenue trend analysis."""

    async def test_revenue_trend_success(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        income_statements: List[IncomeStatement]
    ):
        """Test successful revenue trend analysis."""
        result = await trend_service.analyze_revenue_trend(company.id)
        
        # Verify structure
        assert "company_id" in result
        assert "company_name" in result
        assert "analysis_period" in result
        assert "revenue_data" in result
        assert "growth_metrics" in result
        assert "regression_analysis" in result
        assert "moving_averages" in result
        
        # Verify revenue data
        assert len(result["revenue_data"]) == 5
        
        # Verify growth metrics
        growth = result["growth_metrics"]
        assert "cagr" in growth
        assert growth["cagr"] > Decimal("0.15")  # ~17% CAGR
        assert growth["cagr"] < Decimal("0.25")
        
        # Verify YoY growth rates
        yoy_rates = growth["yoy_growth_rates"]
        assert len(yoy_rates) == 4  # 5 years = 4 YoY rates
        assert all(rate > Decimal("0.15") for rate in yoy_rates)

    async def test_revenue_trend_regression(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        income_statements: List[IncomeStatement]
    ):
        """Test linear regression in revenue trend."""
        result = await trend_service.analyze_revenue_trend(company.id)
        
        regression = result["regression_analysis"]
        
        # Verify regression components
        assert "slope" in regression
        assert "intercept" in regression
        assert "r_squared" in regression
        assert "p_value" in regression
        
        # Positive slope (upward trend)
        assert regression["slope"] > 0
        
        # High R² (good fit)
        assert regression["r_squared"] > 0.85

    async def test_revenue_trend_no_data(
        self,
        trend_service: TrendAnalysisService,
        company: Company
    ):
        """Test revenue trend with no income statements."""
        # Create new company without statements
        new_company = Company(
            id=uuid4(),
            ticker="NODATA",
            name_en="No Data Company",
            name_fa="شرکت بدون داده",
            sector_en="Test",
            sector_fa="تست",
            industry_en="Test",
            industry_fa="تست",
            tenant_id=trend_service.tenant_id,
            is_active=True
        )
        trend_service.db.add(new_company)
        await trend_service.db.commit()
        
        result = await trend_service.analyze_revenue_trend(new_company.id)
        
        # Should return empty or minimal result
        assert result["revenue_data"] == []


@pytest.mark.asyncio
class TestProfitabilityTrendAnalysis:
    """Test profitability trend analysis."""

    async def test_profitability_trend_success(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        income_statements: List[IncomeStatement],
        balance_sheets: List[BalanceSheet],
        financial_ratios: List[FinancialRatio]
    ):
        """Test successful profitability trend analysis."""
        result = await trend_service.analyze_profitability_trends(company.id)
        
        # Verify structure
        assert "company_id" in result
        assert "margins" in result
        assert "returns" in result
        assert "trends" in result
        
        # Verify margins
        margins = result["margins"]
        assert "gross_margin" in margins
        assert "operating_margin" in margins
        assert "net_margin" in margins
        
        # Verify margin stability (should be constant in test data)
        gross_margins = margins["gross_margin"]
        assert len(gross_margins) == 5
        assert all(abs(m["value"] - Decimal("0.60")) < Decimal("0.01") for m in gross_margins)

    async def test_profitability_roe_roa_trends(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        income_statements: List[IncomeStatement],
        balance_sheets: List[BalanceSheet],
        financial_ratios: List[FinancialRatio]
    ):
        """Test ROE and ROA trend analysis."""
        result = await trend_service.analyze_profitability_trends(company.id)
        
        returns = result["returns"]
        
        # Verify ROE data
        assert "roe" in returns
        roe_data = returns["roe"]
        assert len(roe_data) == 5
        
        # ROE should increase over time (0.12, 0.13, 0.14, 0.15, 0.16)
        roe_values = [d["value"] for d in roe_data]
        assert roe_values == sorted(roe_values)  # Increasing trend

    async def test_profitability_trend_analysis(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        income_statements: List[IncomeStatement],
        balance_sheets: List[BalanceSheet],
        financial_ratios: List[FinancialRatio]
    ):
        """Test trend detection in profitability analysis."""
        result = await trend_service.analyze_profitability_trends(company.id)
        
        trends = result["trends"]
        
        # Verify trend indicators
        assert "gross_margin_trend" in trends
        assert "roe_trend" in trends
        
        # ROE should show improving trend
        assert trends["roe_trend"] in ["improving", "stable"]


@pytest.mark.asyncio
class TestRatioTrendAnalysis:
    """Test individual ratio trend analysis."""

    async def test_ratio_trend_success(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        financial_ratios: List[FinancialRatio]
    ):
        """Test successful ratio trend analysis."""
        result = await trend_service.analyze_ratio_trend(
            company.id,
            "return_on_equity"
        )
        
        # Verify structure
        assert "company_id" in result
        assert "ratio_name" in result
        assert "data_points" in result
        assert "statistics" in result
        assert "regression" in result
        
        # Verify data points
        assert len(result["data_points"]) == 5

    async def test_ratio_trend_statistics(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        financial_ratios: List[FinancialRatio]
    ):
        """Test statistical analysis in ratio trend."""
        result = await trend_service.analyze_ratio_trend(
            company.id,
            "return_on_equity"
        )
        
        stats_data = result["statistics"]
        
        # Verify statistical measures
        assert "mean" in stats_data
        assert "median" in stats_data
        assert "std_dev" in stats_data
        assert "min" in stats_data
        assert "max" in stats_data
        
        # Mean should be around 0.14 (0.12 + 0.13 + 0.14 + 0.15 + 0.16) / 5
        assert Decimal("0.13") < stats_data["mean"] < Decimal("0.15")

    async def test_ratio_trend_invalid_ratio(
        self,
        trend_service: TrendAnalysisService,
        company: Company,
        financial_ratios: List[FinancialRatio]
    ):
        """Test ratio trend with invalid ratio name."""
        with pytest.raises(ValueError, match="Invalid ratio name"):
            await trend_service.analyze_ratio_trend(
                company.id,
                "invalid_ratio_name"
            )


class TestMovingAverages:
    """Test moving average calculations."""

    def test_moving_average_3_period(self, trend_service: TrendAnalysisService):
        """Test 3-period moving average."""
        values = [
            Decimal("100"),
            Decimal("120"),
            Decimal("150"),
            Decimal("180"),
            Decimal("200")
        ]
        
        ma3 = trend_service.calculate_moving_average(values, window=3)
        
        # Should have 3 values (5 - 3 + 1 = 3)
        assert len(ma3) == 3
        
        # First MA3 = (100 + 120 + 150) / 3 = 123.33
        assert abs(ma3[0] - Decimal("123.33")) < Decimal("0.1")
        
        # Last MA3 = (150 + 180 + 200) / 3 = 176.67
        assert abs(ma3[2] - Decimal("176.67")) < Decimal("0.1")

    def test_moving_average_5_period(self, trend_service: TrendAnalysisService):
        """Test 5-period moving average."""
        values = [
            Decimal("100"),
            Decimal("120"),
            Decimal("150"),
            Decimal("180"),
            Decimal("200")
        ]
        
        ma5 = trend_service.calculate_moving_average(values, window=5)
        
        # Should have 1 value (5 - 5 + 1 = 1)
        assert len(ma5) == 1
        
        # MA5 = (100 + 120 + 150 + 180 + 200) / 5 = 150
        assert ma5[0] == Decimal("150")

    def test_moving_average_insufficient_data(self, trend_service: TrendAnalysisService):
        """Test moving average with insufficient data."""
        values = [Decimal("100"), Decimal("120")]
        
        ma3 = trend_service.calculate_moving_average(values, window=3)
        
        # Should return empty list
        assert ma3 == []


class TestAnomalyDetection:
    """Test anomaly detection methods."""

    def test_anomaly_detection_zscore(self, trend_service: TrendAnalysisService):
        """Test Z-score based anomaly detection."""
        # Normal data + 1 outlier
        values = [
            Decimal("100"),
            Decimal("105"),
            Decimal("110"),
            Decimal("108"),
            Decimal("500"),  # Outlier
            Decimal("112"),
            Decimal("115")
        ]
        
        anomalies = trend_service.detect_anomalies(values, threshold=2.0)
        
        # Should detect the outlier at index 4
        assert 4 in anomalies
        assert len(anomalies) == 1

    def test_anomaly_detection_no_anomalies(self, trend_service: TrendAnalysisService):
        """Test anomaly detection with normal data."""
        values = [
            Decimal("100"),
            Decimal("105"),
            Decimal("110"),
            Decimal("108"),
            Decimal("112"),
            Decimal("115")
        ]
        
        anomalies = trend_service.detect_anomalies(values, threshold=2.0)
        
        # Should detect no anomalies
        assert len(anomalies) == 0

    def test_anomaly_detection_custom_threshold(self, trend_service: TrendAnalysisService):
        """Test anomaly detection with custom threshold."""
        values = [
            Decimal("100"),
            Decimal("105"),
            Decimal("110"),
            Decimal("150"),  # Moderate outlier
            Decimal("108"),
            Decimal("112")
        ]
        
        # Strict threshold (should detect)
        strict_anomalies = trend_service.detect_anomalies(values, threshold=1.5)
        assert len(strict_anomalies) > 0
        
        # Lenient threshold (might not detect)
        lenient_anomalies = trend_service.detect_anomalies(values, threshold=3.0)
        # May or may not detect depending on Z-score


class TestLinearRegression:
    """Test linear regression analysis."""

    def test_regression_positive_trend(self, trend_service: TrendAnalysisService):
        """Test linear regression with positive trend."""
        x_values = [1, 2, 3, 4, 5]
        y_values = [
            Decimal("100"),
            Decimal("120"),
            Decimal("140"),
            Decimal("160"),
            Decimal("180")
        ]
        
        result = trend_service.perform_linear_regression(x_values, y_values)
        
        # Verify structure
        assert "slope" in result
        assert "intercept" in result
        assert "r_squared" in result
        assert "p_value" in result
        
        # Positive slope (~20)
        assert result["slope"] > 15
        assert result["slope"] < 25
        
        # Perfect fit (R² ≈ 1.0)
        assert result["r_squared"] > 0.99

    def test_regression_negative_trend(self, trend_service: TrendAnalysisService):
        """Test linear regression with negative trend."""
        x_values = [1, 2, 3, 4, 5]
        y_values = [
            Decimal("200"),
            Decimal("180"),
            Decimal("160"),
            Decimal("140"),
            Decimal("120")
        ]
        
        result = trend_service.perform_linear_regression(x_values, y_values)
        
        # Negative slope
        assert result["slope"] < 0

    def test_regression_no_trend(self, trend_service: TrendAnalysisService):
        """Test linear regression with flat trend."""
        x_values = [1, 2, 3, 4, 5]
        y_values = [
            Decimal("100"),
            Decimal("100"),
            Decimal("100"),
            Decimal("100"),
            Decimal("100")
        ]
        
        result = trend_service.perform_linear_regression(x_values, y_values)
        
        # Zero slope
        assert abs(result["slope"]) < 0.01
        
        # R² should be undefined or 0
        # (constant y-values have no variance)


@pytest.mark.asyncio
class TestMultiTenancy:
    """Test multi-tenancy isolation."""

    async def test_revenue_trend_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        income_statements: List[IncomeStatement],
        test_tenant_id: str
    ):
        """Test that revenue trend analysis respects tenant isolation."""
        # Create service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = TrendAnalysisService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should not find company from different tenant
        result = await service_other_tenant.analyze_revenue_trend(company.id)
        
        # Should return empty or error
        assert result["revenue_data"] == []

    async def test_profitability_trend_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        income_statements: List[IncomeStatement],
        balance_sheets: List[BalanceSheet],
        financial_ratios: List[FinancialRatio],
        test_tenant_id: str
    ):
        """Test profitability trend tenant isolation."""
        different_tenant = str(uuid4())
        service_other_tenant = TrendAnalysisService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        result = await service_other_tenant.analyze_profitability_trends(company.id)
        
        # Should not access data from different tenant
        assert result.get("margins", {}).get("gross_margin", []) == []
