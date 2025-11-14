"""
Financial ratio schemas for request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FinancialRatioBase(BaseModel):
    """Base schema for financial ratios."""

    company_id: UUID
    calculation_date: date = Field(..., description="Date ratios were calculated")
    period_end_date: Optional[date] = Field(None, description="Financial period end date")

    # Liquidity ratios
    current_ratio: Optional[Decimal] = Field(None, description="Current Assets / Current Liabilities")
    quick_ratio: Optional[Decimal] = Field(None, description="(Current Assets - Inventory) / Current Liabilities")
    cash_ratio: Optional[Decimal] = Field(None, description="Cash / Current Liabilities")
    working_capital: Optional[Decimal] = Field(None, description="Current Assets - Current Liabilities")
    working_capital_ratio: Optional[Decimal] = Field(None, description="Working Capital / Total Assets")

    # Profitability ratios
    gross_profit_margin: Optional[Decimal] = Field(None, description="Gross Profit / Revenue")
    operating_profit_margin: Optional[Decimal] = Field(None, description="Operating Income / Revenue")
    net_profit_margin: Optional[Decimal] = Field(None, description="Net Income / Revenue")
    return_on_assets: Optional[Decimal] = Field(None, description="Net Income / Total Assets (ROA)")
    return_on_equity: Optional[Decimal] = Field(None, description="Net Income / Shareholders Equity (ROE)")
    return_on_invested_capital: Optional[Decimal] = Field(None, description="NOPAT / Invested Capital (ROIC)")
    ebitda_margin: Optional[Decimal] = Field(None, description="EBITDA / Revenue")
    earnings_quality: Optional[Decimal] = Field(None, description="Operating Cash Flow / Net Income")

    # Leverage ratios
    debt_to_equity: Optional[Decimal] = Field(None, description="Total Debt / Total Equity")
    debt_to_assets: Optional[Decimal] = Field(None, description="Total Debt / Total Assets")
    equity_multiplier: Optional[Decimal] = Field(None, description="Total Assets / Total Equity")
    interest_coverage: Optional[Decimal] = Field(None, description="EBIT / Interest Expense")
    debt_service_coverage: Optional[Decimal] = Field(None, description="Operating Income / Debt Service")
    financial_leverage: Optional[Decimal] = Field(None, description="Total Assets / Equity")

    # Efficiency ratios
    asset_turnover: Optional[Decimal] = Field(None, description="Revenue / Average Total Assets")
    inventory_turnover: Optional[Decimal] = Field(None, description="COGS / Average Inventory")
    receivables_turnover: Optional[Decimal] = Field(None, description="Revenue / Average Receivables")
    payables_turnover: Optional[Decimal] = Field(None, description="COGS / Average Payables")
    days_sales_outstanding: Optional[Decimal] = Field(None, description="365 / Receivables Turnover")
    days_inventory_outstanding: Optional[Decimal] = Field(None, description="365 / Inventory Turnover")
    days_payables_outstanding: Optional[Decimal] = Field(None, description="365 / Payables Turnover")
    cash_conversion_cycle: Optional[Decimal] = Field(None, description="DSO + DIO - DPO")
    fixed_asset_turnover: Optional[Decimal] = Field(None, description="Revenue / Fixed Assets")

    # Market value ratios
    price_to_earnings: Optional[Decimal] = Field(None, description="Market Price / EPS (P/E)")
    price_to_book: Optional[Decimal] = Field(None, description="Market Price / Book Value per Share (P/B)")
    price_to_sales: Optional[Decimal] = Field(None, description="Market Cap / Revenue (P/S)")
    price_to_cash_flow: Optional[Decimal] = Field(None, description="Market Price / Operating CF per Share")
    enterprise_value_to_ebitda: Optional[Decimal] = Field(None, description="EV / EBITDA")
    enterprise_value_to_revenue: Optional[Decimal] = Field(None, description="EV / Revenue")
    market_cap_to_book_value: Optional[Decimal] = Field(None, description="Market Cap / Book Value")
    dividend_yield: Optional[Decimal] = Field(None, description="Annual Dividend / Stock Price")
    dividend_payout_ratio: Optional[Decimal] = Field(None, description="Dividends / Net Income")
    earnings_yield: Optional[Decimal] = Field(None, description="EPS / Stock Price")
    peg_ratio: Optional[Decimal] = Field(None, description="P/E / EPS Growth Rate")

    # Growth ratios
    revenue_growth: Optional[Decimal] = Field(None, description="YoY Revenue Growth %")
    earnings_growth: Optional[Decimal] = Field(None, description="YoY Earnings Growth %")
    book_value_growth: Optional[Decimal] = Field(None, description="YoY Book Value Growth %")
    operating_cash_flow_growth: Optional[Decimal] = Field(None, description="YoY OCF Growth %")
    free_cash_flow_growth: Optional[Decimal] = Field(None, description="YoY FCF Growth %")

    # Cash flow ratios
    operating_cash_flow_ratio: Optional[Decimal] = Field(None, description="OCF / Current Liabilities")
    free_cash_flow_to_equity: Optional[Decimal] = Field(None, description="FCF / Market Cap")
    cash_flow_to_debt: Optional[Decimal] = Field(None, description="OCF / Total Debt")
    capex_to_revenue: Optional[Decimal] = Field(None, description="CapEx / Revenue")


class FinancialRatioCreate(FinancialRatioBase):
    """Schema for creating financial ratios."""

    pass


class FinancialRatioResponse(FinancialRatioBase):
    """Schema for financial ratio response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RatioCalculationRequest(BaseModel):
    """Schema for requesting ratio calculation."""

    company_id: UUID
    period_end_date: date = Field(..., description="Financial period to calculate ratios for")
    include_ratios: Optional[list[str]] = Field(
        None, description="Specific ratios to calculate (if None, calculate all)"
    )


class RatioComparisonRequest(BaseModel):
    """Schema for comparing ratios across periods or companies."""

    company_ids: list[UUID] = Field(..., description="Companies to compare")
    start_date: date = Field(..., description="Start date for comparison")
    end_date: date = Field(..., description="End date for comparison")
    ratios: list[str] = Field(..., description="Ratios to compare")
