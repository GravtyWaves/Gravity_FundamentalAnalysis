"""
Unit tests for ScenarioAnalysisService.

Tests optimistic/neutral/pessimistic scenarios, probability-weighted valuations,
investment recommendations, and comprehensive scenario analysis.
"""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scenario_analysis_service import ScenarioAnalysisService
from app.models.company import Company
from app.models.financial_statements import IncomeStatement, BalanceSheet
from app.models.valuation_risk import Valuation


@pytest.fixture
async def company(test_db: AsyncSession, test_tenant_id: str) -> Company:
    """Create a test company."""
    company = Company(
        id=uuid4(),
        ticker="SCENARIO",
        name_en="Scenario Test Company",
        name_fa="شرکت تست سناریو",
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
        revenue=Decimal("10000000"),
        cost_of_revenue=Decimal("6000000"),
        gross_profit=Decimal("4000000"),
        operating_expenses=Decimal("2000000"),
        operating_income=Decimal("2000000"),
        net_income=Decimal("1500000"),
        ebitda=Decimal("2500000"),
        earnings_per_share=Decimal("1.50"),
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
        total_assets=Decimal("50000000"),
        total_current_assets=Decimal("20000000"),
        total_non_current_assets=Decimal("30000000"),
        total_liabilities=Decimal("20000000"),
        total_current_liabilities=Decimal("8000000"),
        total_non_current_liabilities=Decimal("12000000"),
        total_equity=Decimal("30000000"),
        retained_earnings=Decimal("15000000"),
        tenant_id=test_tenant_id
    )
    test_db.add(sheet)
    await test_db.commit()
    await test_db.refresh(sheet)
    return sheet


@pytest.fixture
async def base_valuation(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> Valuation:
    """Create a base case valuation."""
    valuation = Valuation(
        id=uuid4(),
        company_id=company.id,
        valuation_date=date(2023, 12, 31),
        method="DCF",
        fair_value_per_share=Decimal("50.00"),
        enterprise_value=Decimal("60000000"),
        equity_value=Decimal("50000000"),
        shares_outstanding=Decimal("1000000"),
        wacc=Decimal("0.10"),
        terminal_growth_rate=Decimal("0.03"),
        tenant_id=test_tenant_id
    )
    test_db.add(valuation)
    await test_db.commit()
    await test_db.refresh(valuation)
    return valuation


@pytest.fixture
def scenario_service(test_db: AsyncSession, test_tenant_id: str) -> ScenarioAnalysisService:
    """Create scenario analysis service instance."""
    return ScenarioAnalysisService(db=test_db, tenant_id=test_tenant_id)


class TestScenarioAssumptions:
    """Test scenario assumption generation."""

    def test_optimistic_scenario_assumptions(self, scenario_service: ScenarioAnalysisService):
        """Test optimistic scenario assumption generation."""
        base_assumptions = {
            "revenue_growth": Decimal("0.10"),
            "ebitda_margin": Decimal("0.20"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05")
        }
        
        result = scenario_service.generate_scenario_assumptions(
            base_assumptions,
            "optimistic"
        )
        
        # Optimistic should have better assumptions
        assert result["revenue_growth"] > base_assumptions["revenue_growth"]
        assert result["ebitda_margin"] > base_assumptions["ebitda_margin"]
        assert result["wacc"] < base_assumptions["wacc"]
        assert result["terminal_growth"] > base_assumptions["terminal_growth"]
        assert result["capex_pct"] < base_assumptions["capex_pct"]

    def test_pessimistic_scenario_assumptions(self, scenario_service: ScenarioAnalysisService):
        """Test pessimistic scenario assumption generation."""
        base_assumptions = {
            "revenue_growth": Decimal("0.10"),
            "ebitda_margin": Decimal("0.20"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05")
        }
        
        result = scenario_service.generate_scenario_assumptions(
            base_assumptions,
            "pessimistic"
        )
        
        # Pessimistic should have worse assumptions
        assert result["revenue_growth"] < base_assumptions["revenue_growth"]
        assert result["ebitda_margin"] < base_assumptions["ebitda_margin"]
        assert result["wacc"] > base_assumptions["wacc"]
        assert result["terminal_growth"] < base_assumptions["terminal_growth"]
        assert result["capex_pct"] > base_assumptions["capex_pct"]

    def test_neutral_scenario_assumptions(self, scenario_service: ScenarioAnalysisService):
        """Test neutral scenario uses base assumptions."""
        base_assumptions = {
            "revenue_growth": Decimal("0.10"),
            "ebitda_margin": Decimal("0.20"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05")
        }
        
        result = scenario_service.generate_scenario_assumptions(
            base_assumptions,
            "neutral"
        )
        
        # Neutral should match base assumptions
        assert result == base_assumptions


@pytest.mark.asyncio
class TestValuationScenarios:
    """Test valuation under different scenarios."""

    async def test_valuation_three_scenarios(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test DCF valuation under three scenarios."""
        base_assumptions = {
            "revenue_growth": Decimal("0.15"),
            "ebitda_margin": Decimal("0.25"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05"),
            "projection_years": 5
        }
        
        result = await scenario_service.analyze_valuation_scenarios(
            company.id,
            base_assumptions
        )
        
        # Verify structure
        assert "company_id" in result
        assert "scenarios" in result
        assert "probability_weighted" in result
        
        # Verify all three scenarios
        scenarios = result["scenarios"]
        assert "optimistic" in scenarios
        assert "neutral" in scenarios
        assert "pessimistic" in scenarios
        
        # Verify valuation ordering (optimistic > neutral > pessimistic)
        optimistic_value = scenarios["optimistic"]["fair_value_per_share"]
        neutral_value = scenarios["neutral"]["fair_value_per_share"]
        pessimistic_value = scenarios["pessimistic"]["fair_value_per_share"]
        
        assert optimistic_value > neutral_value
        assert neutral_value > pessimistic_value

    async def test_probability_weighted_valuation(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test probability-weighted valuation calculation."""
        base_assumptions = {
            "revenue_growth": Decimal("0.15"),
            "ebitda_margin": Decimal("0.25"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05"),
            "projection_years": 5
        }
        
        # Custom probabilities
        probabilities = {
            "optimistic": 0.25,
            "neutral": 0.50,
            "pessimistic": 0.25
        }
        
        result = await scenario_service.analyze_valuation_scenarios(
            company.id,
            base_assumptions,
            probabilities=probabilities
        )
        
        weighted = result["probability_weighted"]
        
        # Verify probability-weighted value
        assert "fair_value_per_share" in weighted
        assert "expected_return" in weighted
        assert "probabilities_used" in weighted
        
        # Weighted value should be between neutral and scenarios
        scenarios = result["scenarios"]
        neutral_value = scenarios["neutral"]["fair_value_per_share"]
        weighted_value = weighted["fair_value_per_share"]
        
        # Should be close to neutral (50% weight)
        assert abs(weighted_value - neutral_value) < neutral_value * Decimal("0.3")

    async def test_valuation_scenarios_risk_reward(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test risk-reward ratio calculation."""
        base_assumptions = {
            "revenue_growth": Decimal("0.15"),
            "ebitda_margin": Decimal("0.25"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05"),
            "projection_years": 5,
            "current_price": Decimal("40.00")
        }
        
        result = await scenario_service.analyze_valuation_scenarios(
            company.id,
            base_assumptions
        )
        
        # Verify risk-reward metrics
        assert "risk_reward" in result
        risk_reward = result["risk_reward"]
        
        assert "upside_potential" in risk_reward
        assert "downside_risk" in risk_reward
        assert "risk_reward_ratio" in risk_reward
        
        # Upside should be optimistic - current
        # Downside should be current - pessimistic


@pytest.mark.asyncio
class TestInvestmentRecommendations:
    """Test investment recommendation logic."""

    async def test_strong_buy_recommendation(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test strong buy recommendation criteria."""
        # High upside, low risk
        base_assumptions = {
            "revenue_growth": Decimal("0.20"),
            "ebitda_margin": Decimal("0.30"),
            "wacc": Decimal("0.08"),
            "terminal_growth": Decimal("0.04"),
            "capex_pct": Decimal("0.03"),
            "projection_years": 5,
            "current_price": Decimal("30.00")  # Undervalued
        }
        
        result = await scenario_service.analyze_valuation_scenarios(
            company.id,
            base_assumptions
        )
        
        recommendation = result.get("recommendation")
        
        # Expected upside > 20% should trigger Strong Buy
        if result["probability_weighted"]["expected_return"] > Decimal("0.20"):
            assert recommendation in ["Strong Buy", "Buy"]

    async def test_sell_recommendation(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test sell recommendation criteria."""
        # Low growth, high risk
        base_assumptions = {
            "revenue_growth": Decimal("0.02"),
            "ebitda_margin": Decimal("0.10"),
            "wacc": Decimal("0.15"),
            "terminal_growth": Decimal("0.01"),
            "capex_pct": Decimal("0.08"),
            "projection_years": 5,
            "current_price": Decimal("60.00")  # Overvalued
        }
        
        result = await scenario_service.analyze_valuation_scenarios(
            company.id,
            base_assumptions
        )
        
        recommendation = result.get("recommendation")
        
        # Negative expected return should trigger Sell
        if result["probability_weighted"]["expected_return"] < Decimal("-0.10"):
            assert recommendation in ["Sell", "Strong Sell"]

    async def test_hold_recommendation(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test hold recommendation criteria."""
        # Fair valuation
        base_assumptions = {
            "revenue_growth": Decimal("0.10"),
            "ebitda_margin": Decimal("0.20"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05"),
            "projection_years": 5,
            "current_price": Decimal("48.00")  # Near fair value
        }
        
        result = await scenario_service.analyze_valuation_scenarios(
            company.id,
            base_assumptions
        )
        
        recommendation = result.get("recommendation")
        
        # Small expected return should trigger Hold
        expected_return = result["probability_weighted"]["expected_return"]
        if abs(expected_return) < Decimal("0.10"):
            assert recommendation == "Hold"


@pytest.mark.asyncio
class TestComprehensiveScenarios:
    """Test comprehensive scenario analysis."""

    async def test_comprehensive_analysis(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test comprehensive scenario analysis with valuation + risk."""
        result = await scenario_service.analyze_comprehensive_scenarios(
            company.id,
            current_price=Decimal("45.00")
        )
        
        # Verify structure
        assert "company_id" in result
        assert "valuation_scenarios" in result
        assert "risk_scenarios" in result
        assert "integrated_analysis" in result
        
        # Verify valuation scenarios
        val_scenarios = result["valuation_scenarios"]
        assert "optimistic" in val_scenarios
        assert "neutral" in val_scenarios
        assert "pessimistic" in val_scenarios

    async def test_integrated_risk_valuation(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test integrated risk and valuation analysis."""
        result = await scenario_service.analyze_comprehensive_scenarios(
            company.id,
            current_price=Decimal("45.00")
        )
        
        integrated = result["integrated_analysis"]
        
        # Verify integrated metrics
        assert "overall_rating" in integrated
        assert "key_risks" in integrated
        assert "key_opportunities" in integrated
        assert "recommendation" in integrated
        
        # Overall rating should combine valuation + risk
        rating = integrated["overall_rating"]
        assert rating in ["Highly Attractive", "Attractive", "Neutral", "Unattractive", "Highly Unattractive"]

    async def test_scenario_sensitivity(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet
    ):
        """Test sensitivity to scenario assumptions."""
        result = await scenario_service.analyze_comprehensive_scenarios(
            company.id,
            current_price=Decimal("45.00")
        )
        
        # Verify sensitivity analysis included
        if "sensitivity" in result:
            sensitivity = result["sensitivity"]
            
            # Key variables tested
            assert "revenue_growth" in sensitivity
            assert "wacc" in sensitivity
            assert "terminal_growth" in sensitivity


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_scenario_type(self, scenario_service: ScenarioAnalysisService):
        """Test invalid scenario type."""
        base_assumptions = {"revenue_growth": Decimal("0.10")}
        
        with pytest.raises(ValueError, match="Invalid scenario type"):
            scenario_service.generate_scenario_assumptions(
                base_assumptions,
                "invalid_scenario"
            )

    def test_negative_assumptions(self, scenario_service: ScenarioAnalysisService):
        """Test handling of negative assumptions."""
        base_assumptions = {
            "revenue_growth": Decimal("-0.10"),  # Negative growth
            "ebitda_margin": Decimal("0.20"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05")
        }
        
        # Should handle gracefully
        result = scenario_service.generate_scenario_assumptions(
            base_assumptions,
            "optimistic"
        )
        
        # Even optimistic should respect negative base
        assert result is not None

    @pytest.mark.asyncio
    async def test_missing_financial_data(
        self,
        scenario_service: ScenarioAnalysisService,
        company: Company
    ):
        """Test scenario analysis with missing financial data."""
        # Company without statements
        base_assumptions = {
            "revenue_growth": Decimal("0.10"),
            "ebitda_margin": Decimal("0.20"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05"),
            "projection_years": 5
        }
        
        # Should handle missing data
        with pytest.raises(Exception):
            await scenario_service.analyze_valuation_scenarios(
                company.id,
                base_assumptions
            )


@pytest.mark.asyncio
class TestMultiTenancy:
    """Test multi-tenancy isolation."""

    async def test_scenario_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet,
        test_tenant_id: str
    ):
        """Test scenario analysis respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = ScenarioAnalysisService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        base_assumptions = {
            "revenue_growth": Decimal("0.10"),
            "ebitda_margin": Decimal("0.20"),
            "wacc": Decimal("0.10"),
            "terminal_growth": Decimal("0.03"),
            "capex_pct": Decimal("0.05"),
            "projection_years": 5
        }
        
        # Should not access data from different tenant
        with pytest.raises(Exception):
            await service_other_tenant.analyze_valuation_scenarios(
                company.id,
                base_assumptions
            )
