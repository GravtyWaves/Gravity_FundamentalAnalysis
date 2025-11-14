"""
Integration tests for ValuationService with database.

Tests end-to-end valuation workflows with actual database operations.
"""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.models.company import Company
from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
from app.models.valuation_risk import MarketData
from app.services.valuation_service import ValuationService


@pytest.fixture
async def sample_company(test_db, test_tenant_id):
    """Create a sample company for testing."""
    company = Company(
        id=uuid4(),
        tenant_id=test_tenant_id,
        ticker="TEST",
        name="Test Company",
        exchange="TSE",
        sector="Technology",
        industry="Software",
    )
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    return company


@pytest.fixture
async def sample_financial_statements(test_db, sample_company, test_tenant_id):
    """Create sample financial statements."""
    # Income Statement
    income_stmt = IncomeStatement(
        id=uuid4(),
        tenant_id=test_tenant_id,
        company_id=sample_company.id,
        period_end_date=date(2024, 12, 31),
        period_type="annual",
        fiscal_year=2024,
        total_revenue=Decimal("1000000"),
        cost_of_revenue=Decimal("400000"),
        gross_profit=Decimal("600000"),
        operating_expenses=Decimal("300000"),
        operating_income=Decimal("300000"),
        net_income=Decimal("250000"),
        ebitda=Decimal("350000"),
        basic_eps=Decimal("10.00"),
        diluted_eps=Decimal("9.50"),
    )
    
    # Balance Sheet
    balance_sheet = BalanceSheet(
        id=uuid4(),
        tenant_id=test_tenant_id,
        company_id=sample_company.id,
        period_end_date=date(2024, 12, 31),
        period_type="annual",
        fiscal_year=2024,
        total_assets=Decimal("5000000"),
        current_assets=Decimal("2000000"),
        cash_and_equivalents=Decimal("500000"),
        inventory=Decimal("300000"),
        accounts_receivable=Decimal("400000"),
        property_plant_equipment=Decimal("2000000"),
        intangible_assets=Decimal("800000"),
        total_liabilities=Decimal("3000000"),
        current_liabilities=Decimal("800000"),
        total_debt=Decimal("1500000"),
        stockholders_equity=Decimal("2000000"),
        retained_earnings=Decimal("1200000"),
        shares_outstanding=Decimal("25000"),
    )
    
    # Cash Flow Statement
    cash_flow = CashFlowStatement(
        id=uuid4(),
        tenant_id=test_tenant_id,
        company_id=sample_company.id,
        period_end_date=date(2024, 12, 31),
        period_type="annual",
        fiscal_year=2024,
        operating_cash_flow=Decimal("280000"),
        investing_cash_flow=Decimal("-150000"),
        financing_cash_flow=Decimal("-50000"),
        free_cash_flow=Decimal("200000"),
        capital_expenditures=Decimal("80000"),
        dividends_paid=Decimal("30000"),
    )
    
    test_db.add_all([income_stmt, balance_sheet, cash_flow])
    await test_db.commit()
    
    return {
        "income_statement": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
    }


@pytest.fixture
async def sample_market_data(test_db, sample_company, test_tenant_id):
    """Create sample market data."""
    market_data = MarketData(
        id=uuid4(),
        tenant_id=test_tenant_id,
        company_id=sample_company.id,
        date=date(2024, 12, 31),
        close_price=Decimal("100.00"),
        volume=Decimal("1000000"),
        market_cap=Decimal("2500000"),
    )
    test_db.add(market_data)
    await test_db.commit()
    await test_db.refresh(market_data)
    return market_data


class TestDCFValuationIntegration:
    """Integration tests for DCF valuation method."""
    
    @pytest.mark.asyncio
    async def test_dcf_valuation_end_to_end(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test complete DCF valuation workflow."""
        service = ValuationService(test_db, test_tenant_id)
        
        valuation = await service.dcf_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
            projection_years=5,
            perpetual_growth_rate=Decimal("0.025"),
            cost_of_equity=Decimal("0.12"),
            cost_of_debt=Decimal("0.06"),
        )
        
        # Verify valuation was created
        assert valuation.id is not None
        assert valuation.company_id == sample_company.id
        assert valuation.method == "DCF"
        assert valuation.fair_value_per_share > 0
        assert valuation.enterprise_value > 0
        assert valuation.equity_value > 0
        assert valuation.current_price == Decimal("100.00")
        
        # Verify upside/downside calculation
        expected_upside = ((valuation.fair_value_per_share - Decimal("100.00")) / Decimal("100.00")) * 100
        assert abs(valuation.upside_downside_percent - expected_upside) < Decimal("0.01")
        
        # Verify assumptions stored
        assert "wacc" in valuation.assumptions
        assert "cost_of_equity" in valuation.assumptions
        assert "cost_of_debt" in valuation.assumptions
        
        # Verify parameters stored
        assert "projection_years" in valuation.parameters
        assert "perpetual_growth_rate" in valuation.parameters
        assert "projected_fcf" in valuation.parameters
        assert "terminal_value" in valuation.parameters
    
    @pytest.mark.asyncio
    async def test_dcf_valuation_missing_statements(self, test_db, sample_company, test_tenant_id):
        """Test DCF valuation fails gracefully without financial statements."""
        service = ValuationService(test_db, test_tenant_id)
        
        with pytest.raises(ValueError, match="No income statement found"):
            await service.dcf_valuation(
                company_id=sample_company.id,
                valuation_date=date(2024, 12, 31),
            )
    
    @pytest.mark.asyncio
    async def test_dcf_valuation_custom_parameters(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test DCF with custom projection parameters."""
        service = ValuationService(test_db, test_tenant_id)
        
        valuation = await service.dcf_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
            projection_years=10,
            perpetual_growth_rate=Decimal("0.03"),
            cost_of_equity=Decimal("0.15"),
            cost_of_debt=Decimal("0.05"),
        )
        
        assert valuation.parameters["projection_years"] == 10
        assert valuation.parameters["perpetual_growth_rate"] == float(Decimal("0.03"))


class TestComparablesValuationIntegration:
    """Integration tests for comparables valuation method."""
    
    @pytest.mark.asyncio
    async def test_comparables_valuation_end_to_end(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test complete comparables valuation workflow."""
        service = ValuationService(test_db, test_tenant_id)
        
        peer_multiples = {
            "pe_ratio": Decimal("15.0"),
            "pb_ratio": Decimal("2.0"),
            "ev_to_ebitda": Decimal("10.0"),
            "ev_to_revenue": Decimal("1.5"),
        }
        
        valuation = await service.comparables_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
            peer_multiples=peer_multiples,
        )
        
        # Verify valuation created
        assert valuation.id is not None
        assert valuation.company_id == sample_company.id
        assert valuation.method == "Comparables"
        assert valuation.fair_value_per_share > 0
        assert valuation.current_price == Decimal("100.00")
        
        # Verify assumptions
        assert "peer_multiples" in valuation.assumptions
        assert valuation.assumptions["peer_multiples"]["pe_ratio"] == float(Decimal("15.0"))
        
        # Verify parameters
        assert "methods_used" in valuation.parameters
        assert "valuations_by_method" in valuation.parameters
        assert len(valuation.parameters["methods_used"]) > 0
    
    @pytest.mark.asyncio
    async def test_comparables_valuation_default_multiples(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test comparables valuation with default industry multiples."""
        service = ValuationService(test_db, test_tenant_id)
        
        valuation = await service.comparables_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
        )
        
        # Should use default multiples
        assert valuation.method == "Comparables"
        assert valuation.fair_value_per_share > 0
        assert "peer_multiples" in valuation.assumptions
    
    @pytest.mark.asyncio
    async def test_comparables_valuation_partial_multiples(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test comparables valuation with only some multiples provided."""
        service = ValuationService(test_db, test_tenant_id)
        
        peer_multiples = {
            "pe_ratio": Decimal("18.0"),
            "pb_ratio": Decimal("2.5"),
        }
        
        valuation = await service.comparables_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
            peer_multiples=peer_multiples,
        )
        
        assert valuation.fair_value_per_share > 0
        # Should use provided multiples for P/E and P/B, defaults for others
        assert valuation.assumptions["peer_multiples"]["pe_ratio"] == float(Decimal("18.0"))


class TestAssetBasedValuationIntegration:
    """Integration tests for asset-based valuation method."""
    
    @pytest.mark.asyncio
    async def test_asset_based_valuation_end_to_end(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test complete asset-based valuation workflow."""
        service = ValuationService(test_db, test_tenant_id)
        
        adjustment_factors = {
            "inventory_adjustment": Decimal("0.75"),
            "receivables_adjustment": Decimal("0.85"),
            "ppe_adjustment": Decimal("1.05"),
            "intangible_adjustment": Decimal("0.40"),
            "tangible_asset_adjustment": Decimal("1.0"),
        }
        
        valuation = await service.asset_based_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
            adjustment_factors=adjustment_factors,
        )
        
        # Verify valuation created
        assert valuation.id is not None
        assert valuation.company_id == sample_company.id
        assert valuation.method == "Asset-Based"
        assert valuation.fair_value_per_share > 0
        assert valuation.equity_value > 0
        assert valuation.current_price == Decimal("100.00")
        
        # Verify assumptions
        assert "adjustment_factors" in valuation.assumptions
        assert valuation.assumptions["adjustment_factors"]["inventory_adjustment"] == float(Decimal("0.75"))
        
        # Verify parameters
        assert "book_value" in valuation.parameters
        assert "adjusted_equity" in valuation.parameters
    
    @pytest.mark.asyncio
    async def test_asset_based_valuation_default_factors(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test asset-based valuation with default adjustment factors."""
        service = ValuationService(test_db, test_tenant_id)
        
        valuation = await service.asset_based_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
        )
        
        # Should use default adjustment factors
        assert valuation.method == "Asset-Based"
        assert valuation.fair_value_per_share > 0
        assert "adjustment_factors" in valuation.assumptions
        
        # Verify default factors applied
        factors = valuation.assumptions["adjustment_factors"]
        assert factors["inventory_adjustment"] == 0.8  # Default 80%
        assert factors["receivables_adjustment"] == 0.9  # Default 90%
    
    @pytest.mark.asyncio
    async def test_asset_based_valuation_conservative(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test asset-based valuation with conservative adjustments."""
        service = ValuationService(test_db, test_tenant_id)
        
        # Very conservative adjustments (deep discounts)
        conservative_factors = {
            "inventory_adjustment": Decimal("0.50"),  # 50% haircut
            "receivables_adjustment": Decimal("0.70"),  # 30% haircut
            "ppe_adjustment": Decimal("0.80"),  # 20% haircut
            "intangible_adjustment": Decimal("0.0"),  # Worthless
            "tangible_asset_adjustment": Decimal("0.90"),
        }
        
        valuation = await service.asset_based_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
            adjustment_factors=conservative_factors,
        )
        
        # Conservative valuation should be lower than book value
        book_value_per_share = Decimal("2000000") / Decimal("25000")  # Equity / Shares
        assert valuation.fair_value_per_share < book_value_per_share
    
    @pytest.mark.asyncio
    async def test_asset_based_valuation_optimistic(
        self, test_db, sample_company, sample_financial_statements, sample_market_data, tenant_id
    ):
        """Test asset-based valuation with optimistic adjustments."""
        service = ValuationService(test_db, test_tenant_id)
        
        # Optimistic adjustments (premiums for replacement cost)
        optimistic_factors = {
            "inventory_adjustment": Decimal("1.0"),  # Full value
            "receivables_adjustment": Decimal("1.0"),  # Full collectibility
            "ppe_adjustment": Decimal("1.20"),  # 20% premium (replacement cost)
            "intangible_adjustment": Decimal("0.80"),  # 80% of book
            "tangible_asset_adjustment": Decimal("1.10"),  # 10% premium
        }
        
        valuation = await service.asset_based_valuation(
            company_id=sample_company.id,
            valuation_date=date(2024, 12, 31),
            adjustment_factors=optimistic_factors,
        )
        
        # Optimistic valuation should be higher than book value
        book_value_per_share = Decimal("2000000") / Decimal("25000")
        assert valuation.fair_value_per_share > book_value_per_share


class TestValuationServiceHelpers:
    """Test helper methods in ValuationService."""
    
    @pytest.mark.asyncio
    async def test_get_latest_income_statement(
        self, test_db, sample_company, sample_financial_statements, tenant_id
    ):
        """Test fetching latest income statement."""
        service = ValuationService(test_db, test_tenant_id)
        
        stmt = await service._get_latest_income_statement(
            sample_company.id, date(2024, 12, 31)
        )
        
        assert stmt is not None
        assert stmt.company_id == sample_company.id
        assert stmt.total_revenue == Decimal("1000000")
    
    @pytest.mark.asyncio
    async def test_get_latest_balance_sheet(
        self, test_db, sample_company, sample_financial_statements, tenant_id
    ):
        """Test fetching latest balance sheet."""
        service = ValuationService(test_db, test_tenant_id)
        
        stmt = await service._get_latest_balance_sheet(
            sample_company.id, date(2024, 12, 31)
        )
        
        assert stmt is not None
        assert stmt.company_id == sample_company.id
        assert stmt.total_assets == Decimal("5000000")
    
    @pytest.mark.asyncio
    async def test_get_latest_cash_flow(
        self, test_db, sample_company, sample_financial_statements, tenant_id
    ):
        """Test fetching latest cash flow statement."""
        service = ValuationService(test_db, test_tenant_id)
        
        stmt = await service._get_latest_cash_flow(
            sample_company.id, date(2024, 12, 31)
        )
        
        assert stmt is not None
        assert stmt.company_id == sample_company.id
        assert stmt.free_cash_flow == Decimal("200000")
    
    @pytest.mark.asyncio
    async def test_get_latest_market_data(
        self, test_db, sample_company, sample_market_data, tenant_id
    ):
        """Test fetching latest market data."""
        service = ValuationService(test_db, test_tenant_id)
        
        data = await service._get_latest_market_data(
            sample_company.id, date(2024, 12, 31)
        )
        
        assert data is not None
        assert data.company_id == sample_company.id
        assert data.close_price == Decimal("100.00")
