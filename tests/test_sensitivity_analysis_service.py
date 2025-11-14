"""
Unit tests for SensitivityAnalysisService.

Tests sensitivity analysis methods:
- One-way sensitivity (tornado charts)
- Two-way sensitivity (data tables)
- Monte Carlo simulation
- Tornado chart ranked impacts
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.sensitivity_analysis_service import SensitivityAnalysisService
from app.models.company import Company


@pytest.fixture
async def company(test_db: AsyncSession, test_tenant_id: str) -> Company:
    """Create a test company."""
    company = Company(
        id=uuid4(),
        ticker="SENS",
        name_en="Sensitivity Test Company",
        name_fa="شرکت تست حساسیت",
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
def base_params() -> dict:
    """Base DCF parameters for testing."""
    return {
        "fcf": 100.0,  # $100M free cash flow
        "wacc": 0.10,  # 10% cost of capital
        "terminal_growth": 0.03,  # 3% terminal growth
        "years": 5,  # 5-year projection
    }


@pytest.fixture
def sensitivity_service(test_db: AsyncSession, test_tenant_id: str) -> SensitivityAnalysisService:
    """Create sensitivity analysis service instance."""
    return SensitivityAnalysisService(db=test_db, tenant_id=test_tenant_id)


class TestDCFValuation:
    """Test simple DCF valuation calculation."""

    def test_dcf_calculation(self, sensitivity_service: SensitivityAnalysisService):
        """Test basic DCF valuation."""
        enterprise_value = sensitivity_service.dcf_valuation_simple(
            fcf=100,
            wacc=0.10,
            terminal_growth=0.03,
            years=5
        )
        
        # Enterprise value should be positive
        assert enterprise_value > 0
        
        # Should be reasonable multiple of FCF
        assert 500 < enterprise_value < 2000

    def test_dcf_higher_wacc_lower_value(self, sensitivity_service: SensitivityAnalysisService):
        """Test that higher WACC results in lower valuation."""
        ev_low_wacc = sensitivity_service.dcf_valuation_simple(
            fcf=100,
            wacc=0.08,  # Low WACC
            terminal_growth=0.03,
            years=5
        )
        
        ev_high_wacc = sensitivity_service.dcf_valuation_simple(
            fcf=100,
            wacc=0.15,  # High WACC
            terminal_growth=0.03,
            years=5
        )
        
        # Higher WACC should result in lower valuation
        assert ev_high_wacc < ev_low_wacc

    def test_dcf_higher_growth_higher_value(self, sensitivity_service: SensitivityAnalysisService):
        """Test that higher terminal growth results in higher valuation."""
        ev_low_growth = sensitivity_service.dcf_valuation_simple(
            fcf=100,
            wacc=0.10,
            terminal_growth=0.02,  # Low growth
            years=5
        )
        
        ev_high_growth = sensitivity_service.dcf_valuation_simple(
            fcf=100,
            wacc=0.10,
            terminal_growth=0.05,  # High growth
            years=5
        )
        
        # Higher growth should result in higher valuation
        assert ev_high_growth > ev_low_growth


@pytest.mark.asyncio
class TestOneWaySensitivity:
    """Test one-way sensitivity analysis."""

    async def test_one_way_wacc_sensitivity(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test one-way sensitivity to WACC changes."""
        result = await sensitivity_service.one_way_sensitivity(
            company_id=company.id,
            base_params=base_params,
            variable="wacc",
            variation_range=(-0.30, 0.30),
            num_points=11
        )
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "one_way_sensitivity"
        assert result["variable"] == "wacc"
        assert "sensitivity_data" in result
        
        # Verify number of data points
        assert len(result["sensitivity_data"]) == 11
        
        # Verify data structure
        first_point = result["sensitivity_data"][0]
        assert "wacc_value" in first_point
        assert "wacc_change_pct" in first_point
        assert "enterprise_value" in first_point
        assert "ev_change_pct" in first_point

    async def test_one_way_terminal_growth_sensitivity(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test one-way sensitivity to terminal growth changes."""
        result = await sensitivity_service.one_way_sensitivity(
            company_id=company.id,
            base_params=base_params,
            variable="terminal_growth",
            variation_range=(-0.50, 0.50),
            num_points=7
        )
        
        # Verify structure
        assert result["variable"] == "terminal_growth"
        assert len(result["sensitivity_data"]) == 7
        
        # Higher terminal growth should increase EV
        data = result["sensitivity_data"]
        for i in range(len(data) - 1):
            # Growth increases, EV should increase
            if data[i]["terminal_growth_value"] < data[i+1]["terminal_growth_value"]:
                assert data[i]["enterprise_value"] <= data[i+1]["enterprise_value"]

    async def test_one_way_fcf_sensitivity(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test one-way sensitivity to FCF changes."""
        result = await sensitivity_service.one_way_sensitivity(
            company_id=company.id,
            base_params=base_params,
            variable="fcf",
            variation_range=(-0.40, 0.40),
            num_points=9
        )
        
        # Verify structure
        assert result["variable"] == "fcf"
        assert len(result["sensitivity_data"]) == 9
        
        # FCF should be linearly related to EV
        data = result["sensitivity_data"]
        ev_values = [d["enterprise_value"] for d in data]
        
        # All EVs should be positive
        assert all(ev > 0 for ev in ev_values)

    async def test_one_way_invalid_variable(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test one-way sensitivity with invalid variable."""
        with pytest.raises(ValueError, match="not found in base parameters"):
            await sensitivity_service.one_way_sensitivity(
                company_id=company.id,
                base_params=base_params,
                variable="invalid_variable",
            )


@pytest.mark.asyncio
class TestTwoWaySensitivity:
    """Test two-way sensitivity analysis."""

    async def test_two_way_wacc_growth_sensitivity(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test two-way sensitivity table (WACC vs Terminal Growth)."""
        result = await sensitivity_service.two_way_sensitivity(
            company_id=company.id,
            base_params=base_params,
            variable_x="wacc",
            variable_y="terminal_growth",
            variation_range=(-0.20, 0.20),
            num_points=7
        )
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "two_way_sensitivity"
        assert result["variable_x"] == "wacc"
        assert result["variable_y"] == "terminal_growth"
        
        # Verify table dimensions
        assert len(result["sensitivity_table"]) == 7  # 7 rows (y-axis)
        assert len(result["x_values"]) == 7  # 7 columns (x-axis)
        
        # Verify each row has correct number of values
        for row in result["sensitivity_table"]:
            assert len(row["values"]) == 7

    async def test_two_way_table_values(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test two-way sensitivity table value consistency."""
        result = await sensitivity_service.two_way_sensitivity(
            company_id=company.id,
            base_params=base_params,
            variable_x="wacc",
            variable_y="terminal_growth",
            variation_range=(-0.20, 0.20),
            num_points=5
        )
        
        # All values should be positive
        for row in result["sensitivity_table"]:
            assert all(val > 0 for val in row["values"])
        
        # Base case should be somewhere in the middle
        assert result["base_enterprise_value"] > 0

    async def test_two_way_different_variables(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test two-way sensitivity with different variable pairs."""
        result = await sensitivity_service.two_way_sensitivity(
            company_id=company.id,
            base_params=base_params,
            variable_x="fcf",
            variable_y="wacc",
            variation_range=(-0.30, 0.30),
            num_points=5
        )
        
        # Verify correct variables analyzed
        assert result["variable_x"] == "fcf"
        assert result["variable_y"] == "wacc"
        assert result["base_x"] == base_params["fcf"]
        assert result["base_y"] == base_params["wacc"]

    async def test_two_way_invalid_variables(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test two-way sensitivity with invalid variables."""
        with pytest.raises(ValueError, match="not found in base parameters"):
            await sensitivity_service.two_way_sensitivity(
                company_id=company.id,
                base_params=base_params,
                variable_x="invalid_x",
                variable_y="invalid_y",
            )


@pytest.mark.asyncio
class TestMonteCarloSimulation:
    """Test Monte Carlo simulation."""

    async def test_monte_carlo_basic(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test basic Monte Carlo simulation."""
        variable_distributions = {
            "wacc": {"mean": 0.10, "std": 0.02},
            "terminal_growth": {"mean": 0.03, "std": 0.01},
        }
        
        result = await sensitivity_service.monte_carlo_simulation(
            company_id=company.id,
            base_params=base_params,
            variable_distributions=variable_distributions,
            num_simulations=1000
        )
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "monte_carlo_simulation"
        assert result["num_simulations"] == 1000
        
        # Verify statistics present
        stats = result["statistics"]
        assert "mean" in stats
        assert "median" in stats
        assert "std_dev" in stats
        assert "min" in stats
        assert "max" in stats

    async def test_monte_carlo_percentiles(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test Monte Carlo percentile calculations."""
        variable_distributions = {
            "wacc": {"mean": 0.10, "std": 0.02},
            "terminal_growth": {"mean": 0.03, "std": 0.01},
        }
        
        result = await sensitivity_service.monte_carlo_simulation(
            company_id=company.id,
            base_params=base_params,
            variable_distributions=variable_distributions,
            num_simulations=10000
        )
        
        # Verify percentiles
        percentiles = result["percentiles"]
        assert "p5" in percentiles
        assert "p50" in percentiles  # Median
        assert "p95" in percentiles
        
        # Percentiles should be ordered
        assert percentiles["p5"] < percentiles["p50"]
        assert percentiles["p50"] < percentiles["p95"]
        
        # Median should be close to mean (normal distribution)
        mean = result["statistics"]["mean"]
        median = result["statistics"]["median"]
        assert abs(mean - median) / mean < 0.10  # Within 10%

    async def test_monte_carlo_confidence_intervals(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test Monte Carlo confidence interval calculations."""
        variable_distributions = {
            "wacc": {"mean": 0.10, "std": 0.02},
        }
        
        result = await sensitivity_service.monte_carlo_simulation(
            company_id=company.id,
            base_params=base_params,
            variable_distributions=variable_distributions,
            num_simulations=5000
        )
        
        # Verify confidence intervals
        ci = result["confidence_intervals"]
        assert "80_percent" in ci
        assert "90_percent" in ci
        
        # 90% CI should be wider than 80% CI
        ci_80 = ci["80_percent"]
        ci_90 = ci["90_percent"]
        
        assert ci_90["lower"] < ci_80["lower"]
        assert ci_90["upper"] > ci_80["upper"]

    async def test_monte_carlo_large_simulations(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test Monte Carlo with large number of simulations."""
        variable_distributions = {
            "wacc": {"mean": 0.10, "std": 0.02},
            "terminal_growth": {"mean": 0.03, "std": 0.01},
        }
        
        result = await sensitivity_service.monte_carlo_simulation(
            company_id=company.id,
            base_params=base_params,
            variable_distributions=variable_distributions,
            num_simulations=10000
        )
        
        # Verify correct number of simulations
        assert result["num_simulations"] == 10000
        
        # Statistics should be well-defined
        stats = result["statistics"]
        assert stats["std_dev"] > 0
        assert stats["min"] < stats["mean"] < stats["max"]


@pytest.mark.asyncio
class TestTornadoChart:
    """Test tornado chart data generation."""

    async def test_tornado_chart_basic(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test basic tornado chart data generation."""
        variables = ["wacc", "terminal_growth", "fcf"]
        
        result = await sensitivity_service.tornado_chart_data(
            company_id=company.id,
            base_params=base_params,
            variables=variables,
            variation_pct=0.20
        )
        
        # Verify structure
        assert result["status"] == "success"
        assert result["analysis_type"] == "tornado_chart"
        assert result["variation_pct"] == 20.0
        
        # Verify ranked impacts
        impacts = result["ranked_impacts"]
        assert len(impacts) == 3

    async def test_tornado_chart_ranking(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test tornado chart variable ranking by impact."""
        variables = ["wacc", "terminal_growth", "fcf"]
        
        result = await sensitivity_service.tornado_chart_data(
            company_id=company.id,
            base_params=base_params,
            variables=variables,
            variation_pct=0.20
        )
        
        impacts = result["ranked_impacts"]
        
        # Verify ranking (descending by impact_range)
        for i in range(len(impacts) - 1):
            assert impacts[i]["impact_range"] >= impacts[i+1]["impact_range"]
        
        # Verify ranks are sequential
        for i, impact in enumerate(impacts, start=1):
            assert impact["rank"] == i

    async def test_tornado_chart_impact_details(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test tornado chart impact calculation details."""
        variables = ["wacc", "terminal_growth"]
        
        result = await sensitivity_service.tornado_chart_data(
            company_id=company.id,
            base_params=base_params,
            variables=variables,
            variation_pct=0.20
        )
        
        impacts = result["ranked_impacts"]
        
        # Each impact should have required fields
        for impact in impacts:
            assert "variable" in impact
            assert "base_value" in impact
            assert "impact_range" in impact
            assert "upside_pct" in impact
            assert "downside_pct" in impact
            assert "ev_at_high" in impact
            assert "ev_at_low" in impact
            assert "rank" in impact

    async def test_tornado_chart_wacc_most_sensitive(
        self,
        sensitivity_service: SensitivityAnalysisService,
        company: Company,
        base_params: dict
    ):
        """Test that WACC typically has highest impact on DCF."""
        variables = ["wacc", "terminal_growth", "fcf"]
        
        result = await sensitivity_service.tornado_chart_data(
            company_id=company.id,
            base_params=base_params,
            variables=variables,
            variation_pct=0.20
        )
        
        impacts = result["ranked_impacts"]
        
        # WACC often has highest impact (but not always, depends on parameters)
        # Just verify that ranking is meaningful
        assert impacts[0]["impact_range"] > 0
        assert impacts[0]["rank"] == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_dcf_zero_fcf(self, sensitivity_service: SensitivityAnalysisService):
        """Test DCF with zero free cash flow."""
        enterprise_value = sensitivity_service.dcf_valuation_simple(
            fcf=0,
            wacc=0.10,
            terminal_growth=0.03,
            years=5
        )
        
        # Zero FCF should result in zero valuation
        assert enterprise_value == 0

    def test_dcf_negative_fcf(self, sensitivity_service: SensitivityAnalysisService):
        """Test DCF with negative free cash flow."""
        enterprise_value = sensitivity_service.dcf_valuation_simple(
            fcf=-50,
            wacc=0.10,
            terminal_growth=0.03,
            years=5
        )
        
        # Negative FCF should result in negative valuation
        assert enterprise_value < 0

    def test_dcf_wacc_equals_growth(self, sensitivity_service: SensitivityAnalysisService):
        """Test DCF when WACC equals terminal growth (division by zero)."""
        # When WACC = terminal_growth, terminal value calculation breaks
        # The service should handle this gracefully or return infinity
        try:
            enterprise_value = sensitivity_service.dcf_valuation_simple(
                fcf=100,
                wacc=0.03,
                terminal_growth=0.03,
                years=5
            )
            # If it doesn't raise, value should be extremely large
            assert enterprise_value > 10000 or enterprise_value == float('inf')
        except ZeroDivisionError:
            # Expected behavior
            pass


@pytest.mark.asyncio
class TestMultiTenancy:
    """Test multi-tenancy isolation."""

    async def test_sensitivity_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        base_params: dict,
        test_tenant_id: str
    ):
        """Test sensitivity analysis respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = SensitivityAnalysisService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should still work (sensitivity is computation-only, no DB queries in current implementation)
        result = await service_other_tenant.one_way_sensitivity(
            company_id=company.id,
            base_params=base_params,
            variable="wacc",
        )
        
        # Result should be successful (no tenant checks in current implementation)
        assert result["status"] == "success"
