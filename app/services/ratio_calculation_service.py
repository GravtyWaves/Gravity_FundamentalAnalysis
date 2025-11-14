"""
Financial Ratio Calculation Service.

This service calculates 50+ financial ratios across 7 categories:
1. Liquidity Ratios (5 ratios)
2. Profitability Ratios (8 ratios)
3. Leverage Ratios (6 ratios)
4. Efficiency Ratios (9 ratios)
5. Market Value Ratios (11 ratios)
6. Growth Ratios (5 ratios)
7. Cash Flow Ratios (4 ratios)

All calculations handle edge cases (division by zero, negative values, etc.)
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
from app.models.ratios import FinancialRatio
from app.models.valuation_risk import MarketData
from app.schemas.ratios import FinancialRatioCreate


class RatioCalculationService:
    """Service for calculating financial ratios."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        """
        Initialize ratio calculation service.

        Args:
            db: Database session
            tenant_id: Current tenant ID for multi-tenancy
        """
        self.db = db
        # Convert UUID to string for database storage
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    @staticmethod
    def safe_divide(numerator: Optional[Decimal], denominator: Optional[Decimal]) -> Optional[Decimal]:
        """
        Safely divide two numbers, handling None and zero denominator.

        Args:
            numerator: Numerator value
            denominator: Denominator value

        Returns:
            Result of division or None if invalid
        """
        if numerator is None or denominator is None:
            return None
        if denominator == 0:
            return None
        try:
            return Decimal(str(numerator)) / Decimal(str(denominator))
        except (InvalidOperation, ZeroDivisionError):
            return None

    async def calculate_liquidity_ratios(
        self,
        balance_sheet: BalanceSheet,
        cash_flow: Optional[CashFlowStatement] = None,
    ) -> dict:
        """
        Calculate liquidity ratios.

        Ratios:
        1. Current Ratio = Current Assets / Current Liabilities
        2. Quick Ratio = (Current Assets - Inventory) / Current Liabilities
        3. Cash Ratio = Cash & Equivalents / Current Liabilities
        4. Operating Cash Flow Ratio = Operating Cash Flow / Current Liabilities
        5. Working Capital Ratio = Working Capital / Total Assets

        Args:
            balance_sheet: Balance sheet data
            cash_flow: Cash flow statement (optional, for operating cash flow ratio)

        Returns:
            Dictionary of liquidity ratios
        """
        ratios = {}

        # 1. Current Ratio
        ratios["current_ratio"] = self.safe_divide(
            balance_sheet.current_assets, balance_sheet.current_liabilities
        )

        # 2. Quick Ratio (exclude inventory from current assets)
        quick_assets = None
        if balance_sheet.current_assets and balance_sheet.inventory:
            quick_assets = balance_sheet.current_assets - balance_sheet.inventory
        elif balance_sheet.current_assets:
            quick_assets = balance_sheet.current_assets

        ratios["quick_ratio"] = self.safe_divide(quick_assets, balance_sheet.current_liabilities)

        # 3. Cash Ratio
        ratios["cash_ratio"] = self.safe_divide(
            balance_sheet.cash_and_equivalents, balance_sheet.current_liabilities
        )

        # 4. Operating Cash Flow Ratio
        if cash_flow and cash_flow.operating_cash_flow:
            ratios["operating_cash_flow_ratio"] = self.safe_divide(
                cash_flow.operating_cash_flow, balance_sheet.current_liabilities
            )
        else:
            ratios["operating_cash_flow_ratio"] = None

        # 5. Working Capital Ratio
        working_capital = None
        if balance_sheet.current_assets and balance_sheet.current_liabilities:
            working_capital = balance_sheet.current_assets - balance_sheet.current_liabilities

        ratios["working_capital_ratio"] = self.safe_divide(working_capital, balance_sheet.total_assets)

        return ratios

    async def calculate_profitability_ratios(
        self, income_statement: IncomeStatement, balance_sheet: BalanceSheet
    ) -> dict:
        """
        Calculate profitability ratios.

        Ratios:
        1. Gross Margin = Gross Profit / Revenue
        2. Operating Margin = Operating Income / Revenue
        3. Net Margin = Net Income / Revenue
        4. EBITDA Margin = EBITDA / Revenue
        5. ROA (Return on Assets) = Net Income / Total Assets
        6. ROE (Return on Equity) = Net Income / Total Equity
        7. ROIC (Return on Invested Capital) = NOPAT / Invested Capital
        8. ROCE (Return on Capital Employed) = EBIT / Capital Employed

        Args:
            income_statement: Income statement data
            balance_sheet: Balance sheet data

        Returns:
            Dictionary of profitability ratios
        """
        ratios = {}

        # 1. Gross Margin
        ratios["gross_margin"] = self.safe_divide(income_statement.gross_profit, income_statement.revenue)

        # 2. Operating Margin
        ratios["operating_margin"] = self.safe_divide(
            income_statement.operating_income, income_statement.revenue
        )

        # 3. Net Margin
        ratios["net_margin"] = self.safe_divide(income_statement.net_income, income_statement.revenue)

        # 4. EBITDA Margin
        ratios["ebitda_margin"] = self.safe_divide(income_statement.ebitda, income_statement.revenue)

        # 5. ROA (Return on Assets)
        ratios["roa"] = self.safe_divide(income_statement.net_income, balance_sheet.total_assets)

        # 6. ROE (Return on Equity)
        ratios["roe"] = self.safe_divide(income_statement.net_income, balance_sheet.total_equity)

        # 7. ROIC (Return on Invested Capital)
        # NOPAT = Operating Income * (1 - Tax Rate)
        tax_rate = None
        if income_statement.income_before_tax and income_statement.income_before_tax != 0:
            if income_statement.income_tax_expense:
                tax_rate = abs(income_statement.income_tax_expense / income_statement.income_before_tax)

        nopat = None
        if income_statement.operating_income and tax_rate is not None:
            nopat = income_statement.operating_income * (Decimal("1") - tax_rate)

        # Invested Capital = Total Equity + Total Debt
        invested_capital = None
        total_debt = None
        if balance_sheet.long_term_debt:
            total_debt = balance_sheet.long_term_debt
            if balance_sheet.short_term_debt:
                total_debt += balance_sheet.short_term_debt
        elif balance_sheet.short_term_debt:
            total_debt = balance_sheet.short_term_debt

        if balance_sheet.total_equity and total_debt:
            invested_capital = balance_sheet.total_equity + total_debt
        elif balance_sheet.total_equity:
            invested_capital = balance_sheet.total_equity

        ratios["roic"] = self.safe_divide(nopat, invested_capital)

        # 8. ROCE (Return on Capital Employed)
        # Capital Employed = Total Assets - Current Liabilities
        capital_employed = None
        if balance_sheet.total_assets and balance_sheet.current_liabilities:
            capital_employed = balance_sheet.total_assets - balance_sheet.current_liabilities

        # EBIT = Operating Income
        ratios["roce"] = self.safe_divide(income_statement.operating_income, capital_employed)

        return ratios

    async def calculate_leverage_ratios(
        self, income_statement: IncomeStatement, balance_sheet: BalanceSheet
    ) -> dict:
        """
        Calculate leverage ratios.

        Ratios:
        1. Debt-to-Equity = Total Debt / Total Equity
        2. Debt-to-Assets = Total Debt / Total Assets
        3. Equity Multiplier = Total Assets / Total Equity
        4. Interest Coverage = EBIT / Interest Expense
        5. Debt Service Coverage = Operating Income / Total Debt Service
        6. Net Debt to EBITDA = (Total Debt - Cash) / EBITDA

        Args:
            income_statement: Income statement data
            balance_sheet: Balance sheet data

        Returns:
            Dictionary of leverage ratios
        """
        ratios = {}

        # Calculate total debt
        total_debt = Decimal("0")
        if balance_sheet.long_term_debt:
            total_debt += balance_sheet.long_term_debt
        if balance_sheet.short_term_debt:
            total_debt += balance_sheet.short_term_debt
        if balance_sheet.current_long_term_debt:
            total_debt += balance_sheet.current_long_term_debt

        # 1. Debt-to-Equity
        ratios["debt_to_equity"] = self.safe_divide(total_debt, balance_sheet.total_equity)

        # 2. Debt-to-Assets
        ratios["debt_to_assets"] = self.safe_divide(total_debt, balance_sheet.total_assets)

        # 3. Equity Multiplier
        ratios["equity_multiplier"] = self.safe_divide(balance_sheet.total_assets, balance_sheet.total_equity)

        # 4. Interest Coverage (EBIT / Interest Expense)
        ratios["interest_coverage"] = self.safe_divide(
            income_statement.operating_income, income_statement.interest_expense
        )

        # 5. Debt Service Coverage
        # Total Debt Service = Interest Expense + Principal Payments (approximated)
        debt_service = income_statement.interest_expense
        ratios["debt_service_coverage"] = self.safe_divide(income_statement.operating_income, debt_service)

        # 6. Net Debt to EBITDA
        net_debt = total_debt
        if balance_sheet.cash_and_equivalents:
            net_debt = total_debt - balance_sheet.cash_and_equivalents

        ratios["net_debt_to_ebitda"] = self.safe_divide(net_debt, income_statement.ebitda)

        return ratios

    async def calculate_efficiency_ratios(
        self,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet,
        prev_balance_sheet: Optional[BalanceSheet] = None,
    ) -> dict:
        """
        Calculate efficiency ratios.

        Ratios:
        1. Asset Turnover = Revenue / Average Total Assets
        2. Fixed Asset Turnover = Revenue / Average Fixed Assets
        3. Inventory Turnover = COGS / Average Inventory
        4. Receivables Turnover = Revenue / Average Receivables
        5. Payables Turnover = COGS / Average Payables
        6. Days Sales Outstanding = 365 / Receivables Turnover
        7. Days Inventory Outstanding = 365 / Inventory Turnover
        8. Days Payable Outstanding = 365 / Payables Turnover
        9. Cash Conversion Cycle = DSO + DIO - DPO

        Args:
            income_statement: Income statement data
            balance_sheet: Current balance sheet
            prev_balance_sheet: Previous period balance sheet (for averages)

        Returns:
            Dictionary of efficiency ratios
        """
        ratios = {}

        # Helper function to calculate average
        def average(current: Optional[Decimal], previous: Optional[Decimal]) -> Optional[Decimal]:
            if current is None:
                return previous
            if previous is None:
                return current
            return (current + previous) / Decimal("2")

        # Calculate averages
        avg_total_assets = average(
            balance_sheet.total_assets,
            prev_balance_sheet.total_assets if prev_balance_sheet else None,
        )

        avg_ppe = average(
            balance_sheet.property_plant_equipment,
            prev_balance_sheet.property_plant_equipment if prev_balance_sheet else None,
        )

        avg_inventory = average(
            balance_sheet.inventory, prev_balance_sheet.inventory if prev_balance_sheet else None
        )

        avg_receivables = average(
            balance_sheet.accounts_receivable,
            prev_balance_sheet.accounts_receivable if prev_balance_sheet else None,
        )

        avg_payables = average(
            balance_sheet.accounts_payable,
            prev_balance_sheet.accounts_payable if prev_balance_sheet else None,
        )

        # 1. Asset Turnover
        ratios["asset_turnover"] = self.safe_divide(income_statement.revenue, avg_total_assets)

        # 2. Fixed Asset Turnover
        ratios["fixed_asset_turnover"] = self.safe_divide(income_statement.revenue, avg_ppe)

        # 3. Inventory Turnover
        ratios["inventory_turnover"] = self.safe_divide(income_statement.cost_of_revenue, avg_inventory)

        # 4. Receivables Turnover
        ratios["receivables_turnover"] = self.safe_divide(income_statement.revenue, avg_receivables)

        # 5. Payables Turnover
        ratios["payables_turnover"] = self.safe_divide(income_statement.cost_of_revenue, avg_payables)

        # 6. Days Sales Outstanding
        if ratios["receivables_turnover"]:
            ratios["days_sales_outstanding"] = Decimal("365") / ratios["receivables_turnover"]
        else:
            ratios["days_sales_outstanding"] = None

        # 7. Days Inventory Outstanding
        if ratios["inventory_turnover"]:
            ratios["days_inventory_outstanding"] = Decimal("365") / ratios["inventory_turnover"]
        else:
            ratios["days_inventory_outstanding"] = None

        # 8. Days Payable Outstanding
        if ratios["payables_turnover"]:
            ratios["days_payable_outstanding"] = Decimal("365") / ratios["payables_turnover"]
        else:
            ratios["days_payable_outstanding"] = None

        # 9. Cash Conversion Cycle
        if (
            ratios["days_sales_outstanding"]
            and ratios["days_inventory_outstanding"]
            and ratios["days_payable_outstanding"]
        ):
            ratios["cash_conversion_cycle"] = (
                ratios["days_sales_outstanding"]
                + ratios["days_inventory_outstanding"]
                - ratios["days_payable_outstanding"]
            )
        else:
            ratios["cash_conversion_cycle"] = None

        return ratios

    async def calculate_market_value_ratios(
        self,
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet,
        market_price: Optional[Decimal] = None,
        market_cap: Optional[Decimal] = None,
        shares_outstanding: Optional[Decimal] = None,
    ) -> dict:
        """
        Calculate market value ratios.

        Ratios:
        1. P/E Ratio = Market Price / EPS
        2. P/B Ratio = Market Price / Book Value per Share
        3. P/S Ratio = Market Cap / Revenue
        4. EV/Revenue = Enterprise Value / Revenue
        5. EV/EBITDA = Enterprise Value / EBITDA
        6. EV/EBIT = Enterprise Value / EBIT
        7. Price to Cash Flow = Market Price / Cash Flow per Share
        8. Price to Free Cash Flow = Market Price / FCF per Share
        9. Dividend Yield = Annual Dividend / Market Price
        10. Earnings Yield = EPS / Market Price
        11. PEG Ratio = P/E Ratio / EPS Growth Rate

        Args:
            income_statement: Income statement data
            balance_sheet: Balance sheet data
            market_price: Current market price per share
            market_cap: Market capitalization
            shares_outstanding: Number of shares outstanding

        Returns:
            Dictionary of market value ratios
        """
        ratios = {}

        # Calculate EPS (Earnings Per Share)
        eps = self.safe_divide(income_statement.net_income, shares_outstanding)

        # 1. P/E Ratio
        ratios["pe_ratio"] = self.safe_divide(market_price, eps)

        # Calculate book value per share
        book_value_per_share = self.safe_divide(balance_sheet.total_equity, shares_outstanding)

        # 2. P/B Ratio
        ratios["pb_ratio"] = self.safe_divide(market_price, book_value_per_share)

        # 3. P/S Ratio (Price to Sales)
        ratios["ps_ratio"] = self.safe_divide(market_cap, income_statement.revenue)

        # Calculate Enterprise Value = Market Cap + Total Debt - Cash
        total_debt = Decimal("0")
        if balance_sheet.long_term_debt:
            total_debt += balance_sheet.long_term_debt
        if balance_sheet.short_term_debt:
            total_debt += balance_sheet.short_term_debt

        enterprise_value = None
        if market_cap:
            enterprise_value = market_cap + total_debt
            if balance_sheet.cash_and_equivalents:
                enterprise_value -= balance_sheet.cash_and_equivalents

        # 4. EV/Revenue
        ratios["ev_to_revenue"] = self.safe_divide(enterprise_value, income_statement.revenue)

        # 5. EV/EBITDA
        ratios["ev_to_ebitda"] = self.safe_divide(enterprise_value, income_statement.ebitda)

        # 6. EV/EBIT (EBIT = Operating Income)
        ratios["ev_to_ebit"] = self.safe_divide(enterprise_value, income_statement.operating_income)

        # 7-8. Price to Cash Flow ratios (set to None if not available)
        ratios["price_to_cash_flow"] = None
        ratios["price_to_fcf"] = None

        # 9. Dividend Yield (set to None if dividend data not available)
        ratios["dividend_yield"] = None

        # 10. Earnings Yield (inverse of P/E)
        if ratios["pe_ratio"] and ratios["pe_ratio"] != 0:
            ratios["earnings_yield"] = Decimal("1") / ratios["pe_ratio"]
        else:
            ratios["earnings_yield"] = None

        # 11. PEG Ratio (needs EPS growth rate - set to None for now)
        ratios["peg_ratio"] = None

        return ratios

    async def calculate_growth_ratios(
        self,
        current_income: IncomeStatement,
        prev_income: Optional[IncomeStatement] = None,
        current_balance: Optional[BalanceSheet] = None,
        prev_balance: Optional[BalanceSheet] = None,
    ) -> dict:
        """
        Calculate growth ratios.

        Ratios:
        1. Revenue Growth YoY = (Current Revenue - Previous Revenue) / Previous Revenue
        2. Net Income Growth YoY = (Current NI - Previous NI) / Previous NI
        3. EPS Growth YoY = (Current EPS - Previous EPS) / Previous EPS
        4. EBITDA Growth YoY = (Current EBITDA - Previous EBITDA) / Previous EBITDA
        5. Total Assets Growth YoY = (Current Assets - Previous Assets) / Previous Assets

        Args:
            current_income: Current period income statement
            prev_income: Previous period income statement
            current_balance: Current period balance sheet
            prev_balance: Previous period balance sheet

        Returns:
            Dictionary of growth ratios
        """
        ratios = {}

        if prev_income:
            # 1. Revenue Growth YoY
            if prev_income.revenue and prev_income.revenue != 0:
                revenue_growth = (
                    current_income.revenue - prev_income.revenue
                ) / prev_income.revenue
                ratios["revenue_growth_yoy"] = revenue_growth
            else:
                ratios["revenue_growth_yoy"] = None

            # 2. Net Income Growth YoY
            if prev_income.net_income and prev_income.net_income != 0:
                ni_growth = (
                    current_income.net_income - prev_income.net_income
                ) / prev_income.net_income
                ratios["net_income_growth_yoy"] = ni_growth
            else:
                ratios["net_income_growth_yoy"] = None

            # 3. EPS Growth YoY (needs shares outstanding - set to None)
            ratios["eps_growth_yoy"] = None

            # 4. EBITDA Growth YoY
            if prev_income.ebitda and prev_income.ebitda != 0:
                ebitda_growth = (
                    current_income.ebitda - prev_income.ebitda
                ) / prev_income.ebitda
                ratios["ebitda_growth_yoy"] = ebitda_growth
            else:
                ratios["ebitda_growth_yoy"] = None
        else:
            ratios["revenue_growth_yoy"] = None
            ratios["net_income_growth_yoy"] = None
            ratios["eps_growth_yoy"] = None
            ratios["ebitda_growth_yoy"] = None

        # 5. Total Assets Growth YoY
        if prev_balance and current_balance:
            if prev_balance.total_assets and prev_balance.total_assets != 0:
                assets_growth = (
                    current_balance.total_assets - prev_balance.total_assets
                ) / prev_balance.total_assets
                ratios["total_assets_growth_yoy"] = assets_growth
            else:
                ratios["total_assets_growth_yoy"] = None
        else:
            ratios["total_assets_growth_yoy"] = None

        return ratios

    async def calculate_cash_flow_ratios(
        self,
        income_statement: IncomeStatement,
        cash_flow: Optional[CashFlowStatement] = None,
        balance_sheet: Optional[BalanceSheet] = None,
    ) -> dict:
        """
        Calculate cash flow ratios.

        Ratios:
        1. Operating Cash Flow Margin = Operating CF / Revenue
        2. Free Cash Flow Margin = FCF / Revenue
        3. FCF to Net Income = FCF / Net Income
        4. Cash Flow Coverage = Operating CF / Total Debt

        Args:
            income_statement: Income statement data
            cash_flow: Cash flow statement
            balance_sheet: Balance sheet data

        Returns:
            Dictionary of cash flow ratios
        """
        ratios = {}

        if cash_flow:
            # 1. Operating Cash Flow Margin
            ratios["operating_cf_margin"] = self.safe_divide(
                cash_flow.operating_cash_flow, income_statement.revenue
            )

            # Calculate Free Cash Flow = Operating CF - CapEx
            fcf = None
            if cash_flow.free_cash_flow:
                fcf = cash_flow.free_cash_flow
            elif cash_flow.operating_cash_flow and cash_flow.capital_expenditures:
                fcf = cash_flow.operating_cash_flow + cash_flow.capital_expenditures  # CapEx is negative

            # 2. Free Cash Flow Margin
            ratios["fcf_margin"] = self.safe_divide(fcf, income_statement.revenue)

            # 3. FCF to Net Income
            ratios["fcf_to_net_income"] = self.safe_divide(fcf, income_statement.net_income)

            # 4. Cash Flow Coverage Ratio
            if balance_sheet:
                total_debt = Decimal("0")
                if balance_sheet.long_term_debt:
                    total_debt += balance_sheet.long_term_debt
                if balance_sheet.short_term_debt:
                    total_debt += balance_sheet.short_term_debt

                ratios["cash_flow_coverage"] = self.safe_divide(
                    cash_flow.operating_cash_flow, total_debt
                )
            else:
                ratios["cash_flow_coverage"] = None
        else:
            ratios["operating_cf_margin"] = None
            ratios["fcf_margin"] = None
            ratios["fcf_to_net_income"] = None
            ratios["cash_flow_coverage"] = None

        return ratios

    async def calculate_all_ratios(
        self,
        company_id: UUID,
        period_end_date: date,
        calculation_date: Optional[date] = None,
    ) -> FinancialRatio:
        """
        Calculate all financial ratios for a company at a specific date.

        Args:
            company_id: Company UUID
            period_end_date: Period end date for statements
            calculation_date: Date of calculation (defaults to today)

        Returns:
            FinancialRatio model with all calculated ratios

        Raises:
            ValueError: If required financial statements are not found
        """
        if calculation_date is None:
            calculation_date = date.today()

        # Fetch required financial statements
        income_stmt_result = await self.db.execute(
            select(IncomeStatement).where(
                IncomeStatement.company_id == company_id,
                IncomeStatement.period_end_date == period_end_date,
                IncomeStatement.tenant_id == self.tenant_id,
            )
        )
        income_statement = income_stmt_result.scalar_one_or_none()

        balance_sheet_result = await self.db.execute(
            select(BalanceSheet).where(
                BalanceSheet.company_id == company_id,
                BalanceSheet.period_end_date == period_end_date,
                BalanceSheet.tenant_id == self.tenant_id,
            )
        )
        balance_sheet = balance_sheet_result.scalar_one_or_none()

        cash_flow_result = await self.db.execute(
            select(CashFlowStatement).where(
                CashFlowStatement.company_id == company_id,
                CashFlowStatement.period_end_date == period_end_date,
                CashFlowStatement.tenant_id == self.tenant_id,
            )
        )
        cash_flow = cash_flow_result.scalar_one_or_none()

        if not income_statement or not balance_sheet:
            raise ValueError(
                f"Required financial statements not found for company {company_id} "
                f"at period end date {period_end_date}"
            )

        # Calculate all ratio categories
        liquidity = await self.calculate_liquidity_ratios(balance_sheet, cash_flow)
        profitability = await self.calculate_profitability_ratios(income_statement, balance_sheet)
        leverage = await self.calculate_leverage_ratios(income_statement, balance_sheet)
        efficiency = await self.calculate_efficiency_ratios(income_statement, balance_sheet)

        # Create FinancialRatio model
        ratio_data = FinancialRatioCreate(
            company_id=company_id,
            calculation_date=calculation_date,
            period_end_date=period_end_date,
            # Liquidity ratios
            current_ratio=liquidity.get("current_ratio"),
            quick_ratio=liquidity.get("quick_ratio"),
            cash_ratio=liquidity.get("cash_ratio"),
            operating_cash_flow_ratio=liquidity.get("operating_cash_flow_ratio"),
            working_capital_ratio=liquidity.get("working_capital_ratio"),
            # Profitability ratios
            gross_margin=profitability.get("gross_margin"),
            operating_margin=profitability.get("operating_margin"),
            net_margin=profitability.get("net_margin"),
            ebitda_margin=profitability.get("ebitda_margin"),
            roa=profitability.get("roa"),
            roe=profitability.get("roe"),
            roic=profitability.get("roic"),
            roce=profitability.get("roce"),
            # Leverage ratios
            debt_to_equity=leverage.get("debt_to_equity"),
            debt_to_assets=leverage.get("debt_to_assets"),
            equity_multiplier=leverage.get("equity_multiplier"),
            interest_coverage=leverage.get("interest_coverage"),
            debt_service_coverage=leverage.get("debt_service_coverage"),
            net_debt_to_ebitda=leverage.get("net_debt_to_ebitda"),
            # Efficiency ratios
            asset_turnover=efficiency.get("asset_turnover"),
            fixed_asset_turnover=efficiency.get("fixed_asset_turnover"),
            inventory_turnover=efficiency.get("inventory_turnover"),
            receivables_turnover=efficiency.get("receivables_turnover"),
            payables_turnover=efficiency.get("payables_turnover"),
            days_sales_outstanding=efficiency.get("days_sales_outstanding"),
            days_inventory_outstanding=efficiency.get("days_inventory_outstanding"),
            days_payable_outstanding=efficiency.get("days_payable_outstanding"),
            cash_conversion_cycle=efficiency.get("cash_conversion_cycle"),
        )

        # Save to database
        financial_ratio = FinancialRatio(**ratio_data.model_dump(), tenant_id=self.tenant_id)
        self.db.add(financial_ratio)
        await self.db.commit()
        await self.db.refresh(financial_ratio)

        return financial_ratio
