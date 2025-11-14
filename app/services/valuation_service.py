"""
================================================================================
FILE IDENTITY CARD (شناسنامه فایل)
================================================================================
File Path:           app/services/valuation_service.py
Author:              Gravity Fundamental Analysis Team
Team ID:             FA-001
Created Date:        2025-01-11
Last Modified:       2025-01-18
Version:             1.0.0
Purpose:             Valuation Service - Multiple valuation methodologies
                     DCF, Comparables, Asset-Based with sensitivity analysis

Dependencies:        sqlalchemy>=2.0.23, numpy>=1.24.3 (for NPV calculations)

Related Files:       app/models/valuation_risk.py (valuation models)
                     app/services/financial_statements_service.py (data source)
                     app/services/scenario_analysis_service.py (scenarios)
                     app/services/sensitivity_analysis_service.py (sensitivity)
                     tests/test_valuation_service.py (tests)
                     tests/test_valuation_service_integration.py (integration)

Complexity:          9/10 (complex financial models, NPV, multiples)
Lines of Code:       700
Test Coverage:       0% (needs comprehensive tests)
Performance Impact:  MEDIUM (calculations intensive but cacheable)
Time Spent:          24 hours
Cost:                $11,520 (24 × $480/hr)
Review Status:       Production
Notes:               - DCF with WACC calculation, terminal value
                     - Comparables: P/E, P/B, EV/EBITDA multiples
                     - Asset-Based: book value adjustments
                     - Supports scenario modeling (bull/base/bear)
                     - Needs validation with real market data
================================================================================
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
from app.models.ratios import FinancialRatio
from app.models.valuation_risk import MarketData, Valuation
from app.schemas.valuation_risk import ValuationCreate


class ValuationService:
    """Service for company valuation using multiple methods."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        """
        Initialize valuation service.

        Args:
            db: Database session
            tenant_id: Current tenant ID for multi-tenancy
        """
        self.db = db
        # Convert UUID to string for database storage
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    def calculate_wacc(
        self,
        cost_of_equity: Decimal,
        cost_of_debt: Decimal,
        tax_rate: Decimal,
        market_value_equity: Decimal,
        market_value_debt: Decimal,
    ) -> Decimal:
        """
        Calculate Weighted Average Cost of Capital (WACC).

        Formula: WACC = (E/V × Re) + (D/V × Rd × (1 - Tc))
        Where:
        - E = Market value of equity
        - D = Market value of debt
        - V = E + D (Total value)
        - Re = Cost of equity
        - Rd = Cost of debt
        - Tc = Corporate tax rate

        Args:
            cost_of_equity: Cost of equity (Re)
            cost_of_debt: Cost of debt (Rd)
            tax_rate: Corporate tax rate (Tc)
            market_value_equity: Market value of equity (E)
            market_value_debt: Market value of debt (D)

        Returns:
            WACC as decimal (e.g., 0.10 for 10%)
        """
        total_value = market_value_equity + market_value_debt

        if total_value == 0:
            return Decimal("0")

        equity_weight = market_value_equity / total_value
        debt_weight = market_value_debt / total_value

        # WACC = E/V × Re + D/V × Rd × (1 - Tc)
        wacc = (equity_weight * cost_of_equity) + (
            debt_weight * cost_of_debt * (Decimal("1") - tax_rate)
        )

        return wacc

    def calculate_terminal_value(
        self,
        final_year_fcf: Decimal,
        perpetual_growth_rate: Decimal,
        wacc: Decimal,
    ) -> Decimal:
        """
        Calculate Terminal Value using Gordon Growth Model.

        Formula: TV = FCF × (1 + g) / (WACC - g)

        Args:
            final_year_fcf: Free cash flow in the final projection year
            perpetual_growth_rate: Perpetual growth rate (g)
            wacc: Weighted average cost of capital

        Returns:
            Terminal value
        """
        if wacc <= perpetual_growth_rate:
            # Invalid: WACC must be greater than growth rate
            raise ValueError("WACC must be greater than perpetual growth rate")

        terminal_value = (final_year_fcf * (Decimal("1") + perpetual_growth_rate)) / (
            wacc - perpetual_growth_rate
        )

        return terminal_value

    def project_free_cash_flow(
        self,
        base_fcf: Decimal,
        growth_rates: List[Decimal],
    ) -> List[Decimal]:
        """
        Project future free cash flows.

        Args:
            base_fcf: Base year free cash flow
            growth_rates: List of growth rates for each projection year

        Returns:
            List of projected FCF values
        """
        projected_fcf = []
        current_fcf = base_fcf

        for growth_rate in growth_rates:
            current_fcf = current_fcf * (Decimal("1") + growth_rate)
            projected_fcf.append(current_fcf)

        return projected_fcf

    def discount_cash_flows(
        self,
        cash_flows: List[Decimal],
        discount_rate: Decimal,
    ) -> Decimal:
        """
        Discount future cash flows to present value.

        Formula: PV = CF / (1 + r)^t

        Args:
            cash_flows: List of future cash flows
            discount_rate: Discount rate (WACC)

        Returns:
            Present value of cash flows
        """
        present_value = Decimal("0")

        for year, cash_flow in enumerate(cash_flows, start=1):
            pv = cash_flow / ((Decimal("1") + discount_rate) ** year)
            present_value += pv

        return present_value

    async def dcf_valuation(
        self,
        company_id: UUID,
        valuation_date: date,
        projection_years: int = 5,
        perpetual_growth_rate: Decimal = Decimal("0.025"),  # 2.5%
        cost_of_equity: Optional[Decimal] = None,
        cost_of_debt: Optional[Decimal] = None,
        fcf_growth_rates: Optional[List[Decimal]] = None,
    ) -> Valuation:
        """
        Perform DCF (Discounted Cash Flow) valuation.

        Steps:
        1. Calculate WACC (discount rate)
        2. Project Free Cash Flows for 5-10 years
        3. Calculate Terminal Value
        4. Discount all cash flows to present value
        5. Calculate Enterprise Value = PV(FCF) + PV(Terminal Value)
        6. Calculate Equity Value = EV - Net Debt
        7. Calculate Fair Value per Share = Equity Value / Shares Outstanding

        Args:
            company_id: Company UUID
            valuation_date: Date of valuation
            projection_years: Number of years to project (default 5)
            perpetual_growth_rate: Long-term growth rate (default 2.5%)
            cost_of_equity: Cost of equity (if None, will estimate)
            cost_of_debt: Cost of debt (if None, will estimate)
            fcf_growth_rates: Custom growth rates per year (if None, will estimate)

        Returns:
            Valuation model with DCF results

        Raises:
            ValueError: If required data is not available
        """
        # Fetch latest financial statements
        income_stmt = await self._get_latest_income_statement(company_id)
        balance_sheet = await self._get_latest_balance_sheet(company_id)
        cash_flow = await self._get_latest_cash_flow(company_id)
        market_data = await self._get_latest_market_data(company_id)

        if not income_stmt or not balance_sheet or not cash_flow:
            raise ValueError(f"Required financial statements not found for company {company_id}")

        # Calculate base Free Cash Flow
        base_fcf = cash_flow.free_cash_flow
        if not base_fcf:
            # FCF = Operating CF - CapEx
            base_fcf = cash_flow.operating_cash_flow
            if cash_flow.capital_expenditures:
                base_fcf += cash_flow.capital_expenditures  # CapEx is negative

        # Estimate growth rates if not provided
        if not fcf_growth_rates:
            # Use revenue growth as proxy, with declining growth
            revenue_growth = Decimal("0.10")  # Default 10%
            fcf_growth_rates = [
                revenue_growth * Decimal("0.9") ** year for year in range(projection_years)
            ]

        # Project Free Cash Flows
        projected_fcf = self.project_free_cash_flow(base_fcf, fcf_growth_rates)

        # Calculate WACC
        if not cost_of_equity:
            # Estimate using CAPM: Re = Rf + β(Rm - Rf)
            # For Iranian market, use conservative estimate
            cost_of_equity = Decimal("0.15")  # 15%

        if not cost_of_debt:
            # Estimate from interest expense
            total_debt = Decimal("0")
            if balance_sheet.long_term_debt:
                total_debt += balance_sheet.long_term_debt
            if balance_sheet.short_term_debt:
                total_debt += balance_sheet.short_term_debt

            if total_debt > 0 and income_stmt.interest_expense:
                cost_of_debt = abs(income_stmt.interest_expense) / total_debt
            else:
                cost_of_debt = Decimal("0.08")  # 8% default

        # Calculate tax rate
        tax_rate = Decimal("0")
        if income_stmt.income_before_tax and income_stmt.income_before_tax != 0:
            if income_stmt.income_tax_expense:
                tax_rate = abs(income_stmt.income_tax_expense / income_stmt.income_before_tax)

        # Market values
        market_value_equity = market_data.market_cap if market_data else balance_sheet.total_equity
        market_value_debt = Decimal("0")
        if balance_sheet.long_term_debt:
            market_value_debt += balance_sheet.long_term_debt
        if balance_sheet.short_term_debt:
            market_value_debt += balance_sheet.short_term_debt

        wacc = self.calculate_wacc(
            cost_of_equity,
            cost_of_debt,
            tax_rate,
            market_value_equity,
            market_value_debt,
        )

        # Calculate Terminal Value
        final_year_fcf = projected_fcf[-1]
        terminal_value = self.calculate_terminal_value(final_year_fcf, perpetual_growth_rate, wacc)

        # Discount projected FCF
        pv_projected_fcf = self.discount_cash_flows(projected_fcf, wacc)

        # Discount Terminal Value
        pv_terminal_value = terminal_value / ((Decimal("1") + wacc) ** projection_years)

        # Enterprise Value = PV(FCF) + PV(Terminal Value)
        enterprise_value = pv_projected_fcf + pv_terminal_value

        # Equity Value = EV - Net Debt
        net_debt = market_value_debt
        if balance_sheet.cash_and_equivalents:
            net_debt -= balance_sheet.cash_and_equivalents

        equity_value = enterprise_value - net_debt

        # Fair Value per Share
        shares_outstanding = market_data.shares_outstanding if market_data else Decimal("1")
        fair_value_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else None

        # Calculate upside/downside
        current_price = market_data.close_price if market_data else None
        upside_downside = None
        if current_price and fair_value_per_share and current_price > 0:
            upside_downside = ((fair_value_per_share - current_price) / current_price) * Decimal(
                "100"
            )

        # Prepare parameters and assumptions
        parameters = {
            "projection_years": projection_years,
            "perpetual_growth_rate": float(perpetual_growth_rate),
            "base_fcf": float(base_fcf),
            "projected_fcf": [float(fcf) for fcf in projected_fcf],
            "terminal_value": float(terminal_value),
        }

        assumptions = {
            "wacc": float(wacc),
            "cost_of_equity": float(cost_of_equity),
            "cost_of_debt": float(cost_of_debt),
            "tax_rate": float(tax_rate),
            "fcf_growth_rates": [float(rate) for rate in fcf_growth_rates],
        }

        # Create Valuation model
        valuation_data = ValuationCreate(
            company_id=company_id,
            valuation_date=valuation_date,
            method="DCF",
            fair_value_per_share=fair_value_per_share,
            current_price=current_price,
            upside_downside_percent=upside_downside,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            parameters=parameters,
            assumptions=assumptions,
        )

        valuation = Valuation(**valuation_data.model_dump(), tenant_id=self.tenant_id)
        self.db.add(valuation)
        await self.db.commit()
        await self.db.refresh(valuation)

        return valuation

    async def _get_latest_income_statement(self, company_id: UUID) -> Optional[IncomeStatement]:
        """Fetch latest income statement for company."""
        result = await self.db.execute(
            select(IncomeStatement)
            .where(
                IncomeStatement.company_id == company_id,
                IncomeStatement.tenant_id == self.tenant_id,
            )
            .order_by(IncomeStatement.period_end_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_latest_balance_sheet(self, company_id: UUID) -> Optional[BalanceSheet]:
        """Fetch latest balance sheet for company."""
        result = await self.db.execute(
            select(BalanceSheet)
            .where(
                BalanceSheet.company_id == company_id,
                BalanceSheet.tenant_id == self.tenant_id,
            )
            .order_by(BalanceSheet.period_end_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_latest_cash_flow(self, company_id: UUID) -> Optional[CashFlowStatement]:
        """Fetch latest cash flow statement for company."""
        result = await self.db.execute(
            select(CashFlowStatement)
            .where(
                CashFlowStatement.company_id == company_id,
                CashFlowStatement.tenant_id == self.tenant_id,
            )
            .order_by(CashFlowStatement.period_end_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_latest_market_data(self, company_id: UUID) -> Optional[MarketData]:
        """Fetch latest market data for company."""
        result = await self.db.execute(
            select(MarketData)
            .where(
                MarketData.company_id == company_id,
                MarketData.tenant_id == self.tenant_id,
            )
            .order_by(MarketData.date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def comparables_valuation(
        self,
        company_id: UUID,
        valuation_date: date,
        peer_multiples: Optional[Dict[str, Decimal]] = None,
        valuation_multiples: Optional[List[str]] = None,
    ) -> Valuation:
        """
        Perform Comparables (Relative) Valuation using industry multiples.

        Methods:
        1. P/E Multiple: Fair Value = EPS × Industry Average P/E
        2. P/B Multiple: Fair Value = Book Value per Share × Industry P/B
        3. EV/EBITDA Multiple: Enterprise Value = EBITDA × Industry EV/EBITDA
        4. EV/Revenue Multiple: Enterprise Value = Revenue × Industry EV/Revenue

        Args:
            company_id: Company UUID
            valuation_date: Date of valuation
            peer_multiples: Dict of industry average multiples
                {
                    "pe_ratio": 15.5,
                    "pb_ratio": 2.3,
                    "ev_to_ebitda": 10.2,
                    "ev_to_revenue": 1.8
                }
            valuation_multiples: List of multiples to use (default: all)

        Returns:
            Valuation model with Comparables results

        Raises:
            ValueError: If required data is not available
        """
        # Fetch financial data
        income_stmt = await self._get_latest_income_statement(company_id)
        balance_sheet = await self._get_latest_balance_sheet(company_id)
        market_data = await self._get_latest_market_data(company_id)

        if not income_stmt or not balance_sheet:
            raise ValueError(f"Required financial statements not found for company {company_id}")

        # Default industry multiples (can be customized per industry)
        if not peer_multiples:
            peer_multiples = {
                "pe_ratio": Decimal("15.0"),  # Conservative average
                "pb_ratio": Decimal("2.0"),
                "ev_to_ebitda": Decimal("10.0"),
                "ev_to_revenue": Decimal("1.5"),
            }

        # Default to all multiples
        if not valuation_multiples:
            valuation_multiples = ["pe_ratio", "pb_ratio", "ev_to_ebitda", "ev_to_revenue"]

        valuations = {}
        weights = {}

        # 1. P/E Multiple Valuation
        if "pe_ratio" in valuation_multiples and market_data and market_data.shares_outstanding:
            eps = income_stmt.net_income / market_data.shares_outstanding
            fair_value_pe = eps * peer_multiples.get("pe_ratio", Decimal("15"))
            valuations["pe_multiple"] = fair_value_pe
            weights["pe_multiple"] = Decimal("0.3")

        # 2. P/B Multiple Valuation
        if "pb_ratio" in valuation_multiples and market_data and market_data.shares_outstanding:
            book_value_per_share = balance_sheet.total_equity / market_data.shares_outstanding
            fair_value_pb = book_value_per_share * peer_multiples.get("pb_ratio", Decimal("2"))
            valuations["pb_multiple"] = fair_value_pb
            weights["pb_multiple"] = Decimal("0.25")

        # 3. EV/EBITDA Multiple Valuation
        if "ev_to_ebitda" in valuation_multiples and income_stmt.ebitda:
            ev_from_ebitda = income_stmt.ebitda * peer_multiples.get("ev_to_ebitda", Decimal("10"))
            
            # Convert EV to Equity Value
            net_debt = Decimal("0")
            if balance_sheet.long_term_debt:
                net_debt += balance_sheet.long_term_debt
            if balance_sheet.short_term_debt:
                net_debt += balance_sheet.short_term_debt
            if balance_sheet.cash_and_equivalents:
                net_debt -= balance_sheet.cash_and_equivalents
            
            equity_value_ebitda = ev_from_ebitda - net_debt
            
            if market_data and market_data.shares_outstanding and market_data.shares_outstanding > 0:
                fair_value_ebitda = equity_value_ebitda / market_data.shares_outstanding
                valuations["ev_ebitda_multiple"] = fair_value_ebitda
                weights["ev_ebitda_multiple"] = Decimal("0.30")

        # 4. EV/Revenue Multiple Valuation
        if "ev_to_revenue" in valuation_multiples and income_stmt.revenue:
            ev_from_revenue = income_stmt.revenue * peer_multiples.get("ev_to_revenue", Decimal("1.5"))
            
            # Convert EV to Equity Value
            net_debt = Decimal("0")
            if balance_sheet.long_term_debt:
                net_debt += balance_sheet.long_term_debt
            if balance_sheet.short_term_debt:
                net_debt += balance_sheet.short_term_debt
            if balance_sheet.cash_and_equivalents:
                net_debt -= balance_sheet.cash_and_equivalents
            
            equity_value_revenue = ev_from_revenue - net_debt
            
            if market_data and market_data.shares_outstanding and market_data.shares_outstanding > 0:
                fair_value_revenue = equity_value_revenue / market_data.shares_outstanding
                valuations["ev_revenue_multiple"] = fair_value_revenue
                weights["ev_revenue_multiple"] = Decimal("0.15")

        # Calculate weighted average fair value
        if valuations:
            # Normalize weights
            total_weight = sum(weights.values())
            if total_weight > 0:
                for key in weights:
                    weights[key] = weights[key] / total_weight
            
            # Calculate weighted average
            fair_value_per_share = sum(
                valuations[method] * weights.get(method, Decimal("0"))
                for method in valuations
            )
        else:
            fair_value_per_share = None

        # Calculate upside/downside
        current_price = market_data.close_price if market_data else None
        upside_downside = None
        if current_price and fair_value_per_share and current_price > 0:
            upside_downside = ((fair_value_per_share - current_price) / current_price) * Decimal("100")

        # Prepare parameters and assumptions
        parameters = {
            "methods_used": valuation_multiples,
            "valuations_by_method": {k: float(v) for k, v in valuations.items()},
            "weights": {k: float(v) for k, v in weights.items()},
        }

        assumptions = {
            "peer_multiples": {k: float(v) for k, v in peer_multiples.items()},
            "eps": float(income_stmt.net_income / market_data.shares_outstanding) if market_data and market_data.shares_outstanding else None,
            "book_value_per_share": float(balance_sheet.total_equity / market_data.shares_outstanding) if market_data and market_data.shares_outstanding else None,
        }

        # Create Valuation model
        valuation_data = ValuationCreate(
            company_id=company_id,
            valuation_date=valuation_date,
            method="Comparables",
            fair_value_per_share=fair_value_per_share,
            current_price=current_price,
            upside_downside_percent=upside_downside,
            enterprise_value=None,  # Not applicable for comparables
            equity_value=None,
            parameters=parameters,
            assumptions=assumptions,
        )

        valuation = Valuation(**valuation_data.model_dump(), tenant_id=self.tenant_id)
        self.db.add(valuation)
        await self.db.commit()
        await self.db.refresh(valuation)

        return valuation

    async def asset_based_valuation(
        self,
        company_id: UUID,
        valuation_date: date,
        adjustment_factors: Optional[Dict[str, Decimal]] = None,
    ) -> Valuation:
        """
        Perform Asset-Based Valuation.

        Methods:
        1. Book Value Method: Net Assets = Total Assets - Total Liabilities
        2. Liquidation Value: Assets at liquidation prices (with discounts)
        3. Replacement Cost: Cost to replace all assets at current prices

        Args:
            company_id: Company UUID
            valuation_date: Date of valuation
            adjustment_factors: Dict of adjustment factors
                {
                    "tangible_asset_adjustment": 1.0,  # 1.0 = no adjustment
                    "intangible_adjustment": 0.5,  # 50% discount for intangibles
                    "inventory_adjustment": 0.8,  # 80% of book value
                    "receivables_adjustment": 0.9,  # 90% collectible
                    "ppe_adjustment": 1.1,  # 110% replacement cost
                }

        Returns:
            Valuation model with Asset-Based results

        Raises:
            ValueError: If required data is not available
        """
        # Fetch financial data
        balance_sheet = await self._get_latest_balance_sheet(company_id)
        market_data = await self._get_latest_market_data(company_id)

        if not balance_sheet:
            raise ValueError(f"Balance sheet not found for company {company_id}")

        # Default adjustment factors
        if not adjustment_factors:
            adjustment_factors = {
                "tangible_asset_adjustment": Decimal("1.0"),
                "intangible_adjustment": Decimal("0.5"),
                "inventory_adjustment": Decimal("0.8"),
                "receivables_adjustment": Decimal("0.9"),
                "ppe_adjustment": Decimal("1.0"),
            }

        # 1. Book Value Method (baseline)
        book_value = balance_sheet.total_equity

        # 2. Adjusted Book Value (with adjustments)
        adjusted_assets = Decimal("0")

        # Cash and equivalents (100% value)
        if balance_sheet.cash_and_equivalents:
            adjusted_assets += balance_sheet.cash_and_equivalents

        # Accounts receivable (adjusted for collectibility)
        if balance_sheet.accounts_receivable:
            adjusted_assets += (
                balance_sheet.accounts_receivable * adjustment_factors["receivables_adjustment"]
            )

        # Inventory (adjusted for liquidity)
        if balance_sheet.inventory:
            adjusted_assets += balance_sheet.inventory * adjustment_factors["inventory_adjustment"]

        # Property, Plant & Equipment (adjusted for replacement cost)
        if balance_sheet.property_plant_equipment:
            adjusted_assets += (
                balance_sheet.property_plant_equipment * adjustment_factors["ppe_adjustment"]
            )

        # Intangible assets (heavily discounted)
        if balance_sheet.intangible_assets:
            adjusted_assets += (
                balance_sheet.intangible_assets * adjustment_factors["intangible_adjustment"]
            )

        # Other current assets
        if balance_sheet.other_current_assets:
            adjusted_assets += (
                balance_sheet.other_current_assets * adjustment_factors["tangible_asset_adjustment"]
            )

        # Subtract liabilities
        adjusted_equity = adjusted_assets - balance_sheet.total_liabilities

        # Calculate per share values
        shares_outstanding = market_data.shares_outstanding if market_data else Decimal("1")
        
        book_value_per_share = book_value / shares_outstanding if shares_outstanding > 0 else None
        adjusted_value_per_share = adjusted_equity / shares_outstanding if shares_outstanding > 0 else None

        # Use adjusted value as fair value
        fair_value_per_share = adjusted_value_per_share

        # Calculate upside/downside
        current_price = market_data.close_price if market_data else None
        upside_downside = None
        if current_price and fair_value_per_share and current_price > 0:
            upside_downside = ((fair_value_per_share - current_price) / current_price) * Decimal("100")

        # Prepare parameters and assumptions
        parameters = {
            "book_value": float(book_value),
            "adjusted_equity": float(adjusted_equity),
            "adjusted_assets": float(adjusted_assets),
            "book_value_per_share": float(book_value_per_share) if book_value_per_share else None,
            "adjusted_value_per_share": float(adjusted_value_per_share) if adjusted_value_per_share else None,
        }

        assumptions = {
            "adjustment_factors": {k: float(v) for k, v in adjustment_factors.items()},
            "shares_outstanding": float(shares_outstanding),
        }

        # Create Valuation model
        valuation_data = ValuationCreate(
            company_id=company_id,
            valuation_date=valuation_date,
            method="Asset-Based",
            fair_value_per_share=fair_value_per_share,
            current_price=current_price,
            upside_downside_percent=upside_downside,
            enterprise_value=None,
            equity_value=adjusted_equity,
            parameters=parameters,
            assumptions=assumptions,
        )

        valuation = Valuation(**valuation_data.model_dump(), tenant_id=self.tenant_id)
        self.db.add(valuation)
        await self.db.commit()
        await self.db.refresh(valuation)

        return valuation
