"""
Financial statement schemas for request/response validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ==================== Income Statement ====================
class IncomeStatementBase(BaseModel):
    """Base schema for income statement."""

    company_id: UUID
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, ge=1, le=4, description="Fiscal quarter (1-4)")
    period_type: Literal["Annual", "Quarterly"] = Field(..., description="Period type")
    period_end_date: date = Field(..., description="Period end date")

    # Revenue
    revenue: Optional[Decimal] = Field(None, description="Total revenue")
    cost_of_revenue: Optional[Decimal] = Field(None, description="Cost of goods/services sold")
    gross_profit: Optional[Decimal] = Field(None, description="Gross profit")

    # Operating expenses
    operating_expenses: Optional[Decimal] = Field(None, description="Total operating expenses")
    research_development: Optional[Decimal] = Field(None, description="R&D expenses")
    selling_general_admin: Optional[Decimal] = Field(None, description="SG&A expenses")

    # Operating income
    operating_income: Optional[Decimal] = Field(None, description="Operating income (EBIT)")
    ebitda: Optional[Decimal] = Field(None, description="EBITDA")

    # Non-operating items
    interest_expense: Optional[Decimal] = Field(None, description="Interest expense")
    interest_income: Optional[Decimal] = Field(None, description="Interest income")
    other_income: Optional[Decimal] = Field(None, description="Other income/expenses")

    # Income before tax
    pretax_income: Optional[Decimal] = Field(None, description="Income before tax")
    income_tax: Optional[Decimal] = Field(None, description="Income tax expense")

    # Net income
    net_income: Optional[Decimal] = Field(None, description="Net income")
    net_income_common: Optional[Decimal] = Field(None, description="Net income to common shareholders")

    # Per share data
    eps_basic: Optional[Decimal] = Field(None, description="Basic EPS")
    eps_diluted: Optional[Decimal] = Field(None, description="Diluted EPS")
    shares_outstanding_basic: Optional[Decimal] = Field(None, description="Weighted average shares (basic)")
    shares_outstanding_diluted: Optional[Decimal] = Field(None, description="Weighted average shares (diluted)")


class IncomeStatementCreate(IncomeStatementBase):
    """Schema for creating income statement."""

    pass


class IncomeStatementResponse(IncomeStatementBase):
    """Schema for income statement response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Balance Sheet ====================
class BalanceSheetBase(BaseModel):
    """Base schema for balance sheet."""

    company_id: UUID
    fiscal_year: int
    fiscal_quarter: Optional[int] = Field(None, ge=1, le=4)
    period_type: Literal["Annual", "Quarterly"]
    period_end_date: date

    # Current assets
    cash_and_equivalents: Optional[Decimal] = None
    short_term_investments: Optional[Decimal] = None
    accounts_receivable: Optional[Decimal] = None
    inventory: Optional[Decimal] = None
    prepaid_expenses: Optional[Decimal] = None
    other_current_assets: Optional[Decimal] = None
    total_current_assets: Optional[Decimal] = None

    # Non-current assets
    property_plant_equipment: Optional[Decimal] = None
    accumulated_depreciation: Optional[Decimal] = None
    goodwill: Optional[Decimal] = None
    intangible_assets: Optional[Decimal] = None
    long_term_investments: Optional[Decimal] = None
    other_non_current_assets: Optional[Decimal] = None
    total_non_current_assets: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None

    # Current liabilities
    accounts_payable: Optional[Decimal] = None
    short_term_debt: Optional[Decimal] = None
    current_portion_long_term_debt: Optional[Decimal] = None
    accrued_liabilities: Optional[Decimal] = None
    deferred_revenue: Optional[Decimal] = None
    other_current_liabilities: Optional[Decimal] = None
    total_current_liabilities: Optional[Decimal] = None

    # Non-current liabilities
    long_term_debt: Optional[Decimal] = None
    deferred_tax_liabilities: Optional[Decimal] = None
    pension_obligations: Optional[Decimal] = None
    other_non_current_liabilities: Optional[Decimal] = None
    total_non_current_liabilities: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None

    # Equity
    common_stock: Optional[Decimal] = None
    preferred_stock: Optional[Decimal] = None
    retained_earnings: Optional[Decimal] = None
    treasury_stock: Optional[Decimal] = None
    additional_paid_in_capital: Optional[Decimal] = None
    accumulated_other_comprehensive_income: Optional[Decimal] = None
    total_equity: Optional[Decimal] = None


class BalanceSheetCreate(BalanceSheetBase):
    """Schema for creating balance sheet."""

    pass


class BalanceSheetResponse(BalanceSheetBase):
    """Schema for balance sheet response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Cash Flow Statement ====================
class CashFlowStatementBase(BaseModel):
    """Base schema for cash flow statement."""

    company_id: UUID
    fiscal_year: int
    fiscal_quarter: Optional[int] = Field(None, ge=1, le=4)
    period_type: Literal["Annual", "Quarterly"]
    period_end_date: date

    # Operating activities
    net_income: Optional[Decimal] = None
    depreciation_amortization: Optional[Decimal] = None
    stock_based_compensation: Optional[Decimal] = None
    deferred_taxes: Optional[Decimal] = None
    changes_working_capital: Optional[Decimal] = None
    accounts_receivable_change: Optional[Decimal] = None
    inventory_change: Optional[Decimal] = None
    accounts_payable_change: Optional[Decimal] = None
    other_operating_activities: Optional[Decimal] = None
    operating_cash_flow: Optional[Decimal] = None

    # Investing activities
    capital_expenditures: Optional[Decimal] = None
    acquisitions: Optional[Decimal] = None
    investments_purchases: Optional[Decimal] = None
    investments_sales: Optional[Decimal] = None
    other_investing_activities: Optional[Decimal] = None
    investing_cash_flow: Optional[Decimal] = None

    # Financing activities
    debt_issued: Optional[Decimal] = None
    debt_repaid: Optional[Decimal] = None
    common_stock_issued: Optional[Decimal] = None
    common_stock_repurchased: Optional[Decimal] = None
    dividends_paid: Optional[Decimal] = None
    other_financing_activities: Optional[Decimal] = None
    financing_cash_flow: Optional[Decimal] = None

    # Summary
    net_cash_flow: Optional[Decimal] = None
    free_cash_flow: Optional[Decimal] = None
    beginning_cash: Optional[Decimal] = None
    ending_cash: Optional[Decimal] = None


class CashFlowStatementCreate(CashFlowStatementBase):
    """Schema for creating cash flow statement."""

    pass


class CashFlowStatementResponse(CashFlowStatementBase):
    """Schema for cash flow statement response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
