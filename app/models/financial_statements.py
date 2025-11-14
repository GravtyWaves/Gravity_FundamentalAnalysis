"""
Financial statements models.

Income Statement, Balance Sheet, and Cash Flow Statement models.
"""

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class IncomeStatement(BaseModel):
    """
    Income Statement model.

    Stores quarterly and annual income statement data.
    """

    __tablename__ = "income_statements"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    period_end_date = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # Annual, Quarterly
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer)  # 1, 2, 3, 4 (null for annual)

    # Revenue
    revenue = Column(Numeric(20, 2), nullable=False)
    cost_of_revenue = Column(Numeric(20, 2))
    gross_profit = Column(Numeric(20, 2))

    # Operating expenses
    research_development = Column(Numeric(20, 2))
    selling_general_admin = Column(Numeric(20, 2))
    operating_expenses = Column(Numeric(20, 2))
    operating_income = Column(Numeric(20, 2))

    # Non-operating items
    interest_expense = Column(Numeric(20, 2))
    interest_income = Column(Numeric(20, 2))
    other_income_expense = Column(Numeric(20, 2))

    # Taxes
    income_before_tax = Column(Numeric(20, 2))
    income_tax_expense = Column(Numeric(20, 2))
    net_income = Column(Numeric(20, 2), nullable=False)

    # Per share
    eps_basic = Column(Numeric(10, 4))
    eps_diluted = Column(Numeric(10, 4))
    weighted_avg_shares_basic = Column(Numeric(15, 0))
    weighted_avg_shares_diluted = Column(Numeric(15, 0))

    # Additional metrics
    ebitda = Column(Numeric(20, 2))
    depreciation_amortization = Column(Numeric(20, 2))

    # Relationships
    company = relationship("Company", back_populates="income_statements")

    def __repr__(self) -> str:
        return f"<IncomeStatement(company_id={self.company_id}, period={self.period_end_date})>"


class BalanceSheet(BaseModel):
    """
    Balance Sheet model.

    Stores quarterly and annual balance sheet data.
    """

    __tablename__ = "balance_sheets"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    period_end_date = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer)

    # Assets
    total_assets = Column(Numeric(20, 2), nullable=False)
    current_assets = Column(Numeric(20, 2))
    cash_and_equivalents = Column(Numeric(20, 2))
    short_term_investments = Column(Numeric(20, 2))
    accounts_receivable = Column(Numeric(20, 2))
    inventory = Column(Numeric(20, 2))
    other_current_assets = Column(Numeric(20, 2))

    non_current_assets = Column(Numeric(20, 2))
    property_plant_equipment = Column(Numeric(20, 2))
    goodwill = Column(Numeric(20, 2))
    intangible_assets = Column(Numeric(20, 2))
    long_term_investments = Column(Numeric(20, 2))
    other_non_current_assets = Column(Numeric(20, 2))

    # Liabilities
    total_liabilities = Column(Numeric(20, 2), nullable=False)
    current_liabilities = Column(Numeric(20, 2))
    accounts_payable = Column(Numeric(20, 2))
    short_term_debt = Column(Numeric(20, 2))
    current_long_term_debt = Column(Numeric(20, 2))
    other_current_liabilities = Column(Numeric(20, 2))

    non_current_liabilities = Column(Numeric(20, 2))
    long_term_debt = Column(Numeric(20, 2))
    deferred_tax_liabilities = Column(Numeric(20, 2))
    other_non_current_liabilities = Column(Numeric(20, 2))

    # Equity
    total_equity = Column(Numeric(20, 2), nullable=False)
    common_stock = Column(Numeric(20, 2))
    retained_earnings = Column(Numeric(20, 2))
    accumulated_other_comprehensive_income = Column(Numeric(20, 2))
    treasury_stock = Column(Numeric(20, 2))
    additional_paid_in_capital = Column(Numeric(20, 2))

    # Relationships
    company = relationship("Company", back_populates="balance_sheets")

    def __repr__(self) -> str:
        return f"<BalanceSheet(company_id={self.company_id}, period={self.period_end_date})>"


class CashFlowStatement(BaseModel):
    """
    Cash Flow Statement model.

    Stores quarterly and annual cash flow data.
    """

    __tablename__ = "cash_flow_statements"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    period_end_date = Column(Date, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer)

    # Operating activities
    net_income = Column(Numeric(20, 2), nullable=False)
    depreciation_amortization = Column(Numeric(20, 2))
    stock_based_compensation = Column(Numeric(20, 2))
    deferred_income_tax = Column(Numeric(20, 2))
    change_in_working_capital = Column(Numeric(20, 2))
    change_in_accounts_receivable = Column(Numeric(20, 2))
    change_in_inventory = Column(Numeric(20, 2))
    change_in_accounts_payable = Column(Numeric(20, 2))
    other_operating_activities = Column(Numeric(20, 2))
    operating_cash_flow = Column(Numeric(20, 2), nullable=False)

    # Investing activities
    capital_expenditures = Column(Numeric(20, 2))
    acquisitions = Column(Numeric(20, 2))
    purchase_of_investments = Column(Numeric(20, 2))
    sale_of_investments = Column(Numeric(20, 2))
    other_investing_activities = Column(Numeric(20, 2))
    investing_cash_flow = Column(Numeric(20, 2))

    # Financing activities
    dividends_paid = Column(Numeric(20, 2))
    stock_repurchase = Column(Numeric(20, 2))
    debt_issued = Column(Numeric(20, 2))
    debt_repaid = Column(Numeric(20, 2))
    common_stock_issued = Column(Numeric(20, 2))
    other_financing_activities = Column(Numeric(20, 2))
    financing_cash_flow = Column(Numeric(20, 2))

    # Net change
    net_change_in_cash = Column(Numeric(20, 2))
    beginning_cash_balance = Column(Numeric(20, 2))
    ending_cash_balance = Column(Numeric(20, 2))

    # Calculated metrics
    free_cash_flow = Column(Numeric(20, 2))  # OCF - CapEx

    # Relationships
    company = relationship("Company", back_populates="cash_flow_statements")

    def __repr__(self) -> str:
        return f"<CashFlowStatement(company_id={self.company_id}, period={self.period_end_date})>"
