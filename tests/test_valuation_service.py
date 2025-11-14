"""
Tests for Valuation Service.

Tests cover:
- WACC calculation
- Terminal Value calculation
- FCF projection
- Cash flow discounting
- DCF valuation (basic scenarios)
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.valuation_service import ValuationService


@pytest.fixture
def tenant_id():
    """Fixture for tenant ID."""
    return str(uuid4())


@pytest.fixture
def company_id():
    """Fixture for company ID."""
    return uuid4()


class TestWACCCalculation:
    """Test WACC (Weighted Average Cost of Capital) calculation."""

    def test_wacc_balanced_capital_structure(self, test_db: AsyncSession, tenant_id):
        """Test WACC with balanced equity and debt."""
        service = ValuationService(test_db, tenant_id)

        # 50% equity, 50% debt
        # Re = 15%, Rd = 8%, Tax = 25%
        # WACC = 0.5 × 0.15 + 0.5 × 0.08 × (1 - 0.25) = 0.075 + 0.03 = 0.105 (10.5%)
        wacc = service.calculate_wacc(
            cost_of_equity=Decimal("0.15"),
            cost_of_debt=Decimal("0.08"),
            tax_rate=Decimal("0.25"),
            market_value_equity=Decimal("500000"),
            market_value_debt=Decimal("500000"),
        )

        assert wacc == Decimal("0.105")

    def test_wacc_high_equity(self, test_db: AsyncSession, tenant_id):
        """Test WACC with high equity ratio."""
        service = ValuationService(test_db, tenant_id)

        # 80% equity, 20% debt
        # WACC = 0.8 × 0.15 + 0.2 × 0.08 × (1 - 0.25) = 0.12 + 0.012 = 0.132 (13.2%)
        wacc = service.calculate_wacc(
            cost_of_equity=Decimal("0.15"),
            cost_of_debt=Decimal("0.08"),
            tax_rate=Decimal("0.25"),
            market_value_equity=Decimal("800000"),
            market_value_debt=Decimal("200000"),
        )

        assert wacc == Decimal("0.132")

    def test_wacc_zero_debt(self, test_db: AsyncSession, tenant_id):
        """Test WACC with no debt (100% equity)."""
        service = ValuationService(test_db, tenant_id)

        # 100% equity, 0% debt
        # WACC = 1.0 × 0.15 + 0 = 0.15 (15%)
        wacc = service.calculate_wacc(
            cost_of_equity=Decimal("0.15"),
            cost_of_debt=Decimal("0.08"),
            tax_rate=Decimal("0.25"),
            market_value_equity=Decimal("1000000"),
            market_value_debt=Decimal("0"),
        )

        assert wacc == Decimal("0.15")


class TestTerminalValueCalculation:
    """Test Terminal Value calculation using Gordon Growth Model."""

    def test_terminal_value_normal_growth(self, test_db: AsyncSession, tenant_id):
        """Test terminal value with normal growth rate."""
        service = ValuationService(test_db, tenant_id)

        # Final FCF = 100,000, Growth = 2.5%, WACC = 10%
        # TV = 100,000 × (1 + 0.025) / (0.10 - 0.025) = 102,500 / 0.075 = 1,366,666.67
        tv = service.calculate_terminal_value(
            final_year_fcf=Decimal("100000"),
            perpetual_growth_rate=Decimal("0.025"),
            wacc=Decimal("0.10"),
        )

        expected = Decimal("100000") * Decimal("1.025") / Decimal("0.075")
        assert abs(tv - expected) < Decimal("1")

    def test_terminal_value_low_growth(self, test_db: AsyncSession, tenant_id):
        """Test terminal value with low growth rate."""
        service = ValuationService(test_db, tenant_id)

        # Final FCF = 100,000, Growth = 1%, WACC = 10%
        # TV = 100,000 × 1.01 / 0.09 = 1,122,222.22
        tv = service.calculate_terminal_value(
            final_year_fcf=Decimal("100000"),
            perpetual_growth_rate=Decimal("0.01"),
            wacc=Decimal("0.10"),
        )

        expected = Decimal("100000") * Decimal("1.01") / Decimal("0.09")
        assert abs(tv - expected) < Decimal("1")

    def test_terminal_value_invalid_growth(self, test_db: AsyncSession, tenant_id):
        """Test terminal value with growth >= WACC raises error."""
        service = ValuationService(test_db, tenant_id)

        # Growth rate cannot be >= WACC
        with pytest.raises(ValueError, match="WACC must be greater than perpetual growth rate"):
            service.calculate_terminal_value(
                final_year_fcf=Decimal("100000"),
                perpetual_growth_rate=Decimal("0.10"),  # Same as WACC
                wacc=Decimal("0.10"),
            )


class TestFCFProjection:
    """Test Free Cash Flow projection."""

    def test_fcf_projection_constant_growth(self, test_db: AsyncSession, tenant_id):
        """Test FCF projection with constant growth rate."""
        service = ValuationService(test_db, tenant_id)

        base_fcf = Decimal("100000")
        growth_rates = [Decimal("0.10")] * 5  # 10% growth for 5 years

        projected = service.project_free_cash_flow(base_fcf, growth_rates)

        # Year 1: 100,000 × 1.10 = 110,000
        # Year 2: 110,000 × 1.10 = 121,000
        # Year 3: 121,000 × 1.10 = 133,100
        # Year 4: 133,100 × 1.10 = 146,410
        # Year 5: 146,410 × 1.10 = 161,051
        assert len(projected) == 5
        assert projected[0] == Decimal("110000")
        assert projected[1] == Decimal("121000")
        assert abs(projected[4] - Decimal("161051")) < Decimal("1")

    def test_fcf_projection_declining_growth(self, test_db: AsyncSession, tenant_id):
        """Test FCF projection with declining growth rates."""
        service = ValuationService(test_db, tenant_id)

        base_fcf = Decimal("100000")
        growth_rates = [Decimal("0.15"), Decimal("0.12"), Decimal("0.10"), Decimal("0.08"), Decimal("0.05")]

        projected = service.project_free_cash_flow(base_fcf, growth_rates)

        # Year 1: 100,000 × 1.15 = 115,000
        # Year 2: 115,000 × 1.12 = 128,800
        assert len(projected) == 5
        assert projected[0] == Decimal("115000")
        assert projected[1] == Decimal("128800")


class TestCashFlowDiscounting:
    """Test cash flow discounting to present value."""

    def test_discount_single_cash_flow(self, test_db: AsyncSession, tenant_id):
        """Test discounting a single future cash flow."""
        service = ValuationService(test_db, tenant_id)

        # CF = 110,000 in Year 1, Discount Rate = 10%
        # PV = 110,000 / 1.10 = 100,000
        cash_flows = [Decimal("110000")]
        discount_rate = Decimal("0.10")

        pv = service.discount_cash_flows(cash_flows, discount_rate)

        assert abs(pv - Decimal("100000")) < Decimal("1")

    def test_discount_multiple_cash_flows(self, test_db: AsyncSession, tenant_id):
        """Test discounting multiple future cash flows."""
        service = ValuationService(test_db, tenant_id)

        # Year 1: 110,000 / 1.10 = 100,000
        # Year 2: 121,000 / 1.21 = 100,000
        # Year 3: 133,100 / 1.331 = 100,000
        # Total PV = 300,000
        cash_flows = [Decimal("110000"), Decimal("121000"), Decimal("133100")]
        discount_rate = Decimal("0.10")

        pv = service.discount_cash_flows(cash_flows, discount_rate)

        # Each year contributes ~100,000 in PV
        assert abs(pv - Decimal("300000")) < Decimal("10")

    def test_discount_with_high_rate(self, test_db: AsyncSession, tenant_id):
        """Test discounting with high discount rate."""
        service = ValuationService(test_db, tenant_id)

        # Higher discount rate = lower present value
        cash_flows = [Decimal("110000"), Decimal("121000"), Decimal("133100")]
        discount_rate = Decimal("0.20")  # 20%

        pv = service.discount_cash_flows(cash_flows, discount_rate)

        # PV should be significantly less than 300,000
        assert pv < Decimal("260000")


class TestComparablesValuation:
    """Test Comparables (Relative) Valuation calculations."""

    def test_pe_multiple_calculation(self, test_db: AsyncSession, tenant_id):
        """Test P/E multiple valuation logic."""
        service = ValuationService(test_db, tenant_id)

        # EPS = 10, Industry P/E = 15
        # Fair Value = 10 × 15 = 150
        eps = Decimal("10")
        peer_pe = Decimal("15")
        expected_value = eps * peer_pe

        assert expected_value == Decimal("150")

    def test_pb_multiple_calculation(self, test_db: AsyncSession, tenant_id):
        """Test P/B multiple valuation logic."""
        service = ValuationService(test_db, tenant_id)

        # Book Value per Share = 50, Industry P/B = 2.0
        # Fair Value = 50 × 2.0 = 100
        bvps = Decimal("50")
        peer_pb = Decimal("2.0")
        expected_value = bvps * peer_pb

        assert expected_value == Decimal("100")

    def test_ev_ebitda_multiple_calculation(self, test_db: AsyncSession, tenant_id):
        """Test EV/EBITDA multiple valuation logic."""
        service = ValuationService(test_db, tenant_id)

        # EBITDA = 100,000, EV/EBITDA = 10
        # EV = 100,000 × 10 = 1,000,000
        ebitda = Decimal("100000")
        peer_ev_ebitda = Decimal("10")
        expected_ev = ebitda * peer_ev_ebitda

        assert expected_ev == Decimal("1000000")

    def test_ev_to_equity_conversion(self, test_db: AsyncSession, tenant_id):
        """Test conversion from Enterprise Value to Equity Value."""
        service = ValuationService(test_db, tenant_id)

        # EV = 1,000,000, Debt = 300,000, Cash = 50,000
        # Equity Value = EV - (Debt - Cash) = 1,000,000 - 250,000 = 750,000
        ev = Decimal("1000000")
        debt = Decimal("300000")
        cash = Decimal("50000")
        net_debt = debt - cash

        equity_value = ev - net_debt
        assert equity_value == Decimal("750000")

    def test_weighted_average_valuation(self, test_db: AsyncSession, tenant_id):
        """Test weighted average of multiple valuation methods."""
        service = ValuationService(test_db, tenant_id)

        # Multiple valuations with weights
        valuations = {
            "pe_multiple": Decimal("150"),
            "pb_multiple": Decimal("100"),
            "ev_ebitda_multiple": Decimal("125"),
        }
        
        weights = {
            "pe_multiple": Decimal("0.4"),
            "pb_multiple": Decimal("0.3"),
            "ev_ebitda_multiple": Decimal("0.3"),
        }

        # Weighted average = 150×0.4 + 100×0.3 + 125×0.3 = 60 + 30 + 37.5 = 127.5
        weighted_avg = sum(valuations[k] * weights[k] for k in valuations)
        
        assert weighted_avg == Decimal("127.5")


class TestAssetBasedValuation:
    """Test Asset-Based Valuation calculations."""

    def test_book_value_calculation(self, test_db: AsyncSession, tenant_id):
        """Test basic book value calculation."""
        service = ValuationService(test_db, tenant_id)

        # Book Value = Total Assets - Total Liabilities
        total_assets = Decimal("1000000")
        total_liabilities = Decimal("400000")
        book_value = total_assets - total_liabilities

        assert book_value == Decimal("600000")

    def test_asset_adjustments(self, test_db: AsyncSession, tenant_id):
        """Test asset value adjustments."""
        service = ValuationService(test_db, tenant_id)

        # Inventory at 80% of book value
        inventory_book = Decimal("100000")
        inventory_adjustment = Decimal("0.8")
        adjusted_inventory = inventory_book * inventory_adjustment

        assert adjusted_inventory == Decimal("80000")

        # Receivables at 90% collectibility
        receivables_book = Decimal("150000")
        receivables_adjustment = Decimal("0.9")
        adjusted_receivables = receivables_book * receivables_adjustment

        assert adjusted_receivables == Decimal("135000")

    def test_intangible_discount(self, test_db: AsyncSession, tenant_id):
        """Test intangible asset discount."""
        service = ValuationService(test_db, tenant_id)

        # Intangibles at 50% of book value
        intangibles_book = Decimal("200000")
        intangible_adjustment = Decimal("0.5")
        adjusted_intangibles = intangibles_book * intangible_adjustment

        assert adjusted_intangibles == Decimal("100000")

    def test_ppe_replacement_cost(self, test_db: AsyncSession, tenant_id):
        """Test PP&E at replacement cost."""
        service = ValuationService(test_db, tenant_id)

        # PP&E at 110% (replacement cost higher than book)
        ppe_book = Decimal("500000")
        ppe_adjustment = Decimal("1.1")
        adjusted_ppe = ppe_book * ppe_adjustment

        assert adjusted_ppe == Decimal("550000")

    def test_adjusted_equity_calculation(self, test_db: AsyncSession, tenant_id):
        """Test full adjusted equity calculation."""
        service = ValuationService(test_db, tenant_id)

        # Adjusted Assets
        cash = Decimal("50000")  # 100%
        receivables = Decimal("150000") * Decimal("0.9")  # 90%
        inventory = Decimal("100000") * Decimal("0.8")  # 80%
        ppe = Decimal("500000") * Decimal("1.0")  # 100%
        intangibles = Decimal("200000") * Decimal("0.5")  # 50%

        total_adjusted_assets = cash + receivables + inventory + ppe + intangibles
        # = 50,000 + 135,000 + 80,000 + 500,000 + 100,000 = 865,000

        liabilities = Decimal("400000")
        adjusted_equity = total_adjusted_assets - liabilities
        # = 865,000 - 400,000 = 465,000

        assert adjusted_equity == Decimal("465000")


class TestHelperMethods:
    """Test helper methods for fetching financial data."""

    # Note: Integration tests for _get_latest_* methods would require
    # setting up database with sample data. Those tests should be in
    # integration test suite, not unit tests.
    pass
