"""
Financial ratios model for storing calculated ratios.

Stores 50+ financial ratios for analysis.
"""

from sqlalchemy import Column, Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class FinancialRatio(BaseModel):
    """
    Financial Ratios model.

    Stores all calculated financial ratios for a company at a specific date.
    """

    __tablename__ = "financial_ratios"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    calculation_date = Column(Date, nullable=False, index=True)
    period_end_date = Column(Date, nullable=False)

    # Liquidity Ratios
    current_ratio = Column(Numeric(10, 4))
    quick_ratio = Column(Numeric(10, 4))
    cash_ratio = Column(Numeric(10, 4))
    operating_cash_flow_ratio = Column(Numeric(10, 4))
    working_capital_ratio = Column(Numeric(10, 4))

    # Profitability Ratios
    gross_margin = Column(Numeric(10, 4))
    operating_margin = Column(Numeric(10, 4))
    net_margin = Column(Numeric(10, 4))
    ebitda_margin = Column(Numeric(10, 4))
    roa = Column(Numeric(10, 4))  # Return on Assets
    roe = Column(Numeric(10, 4))  # Return on Equity
    roic = Column(Numeric(10, 4))  # Return on Invested Capital
    roce = Column(Numeric(10, 4))  # Return on Capital Employed

    # Leverage Ratios
    debt_to_equity = Column(Numeric(10, 4))
    debt_to_assets = Column(Numeric(10, 4))
    equity_multiplier = Column(Numeric(10, 4))
    interest_coverage = Column(Numeric(10, 4))
    debt_service_coverage = Column(Numeric(10, 4))
    net_debt_to_ebitda = Column(Numeric(10, 4))

    # Efficiency Ratios
    asset_turnover = Column(Numeric(10, 4))
    fixed_asset_turnover = Column(Numeric(10, 4))
    inventory_turnover = Column(Numeric(10, 4))
    receivables_turnover = Column(Numeric(10, 4))
    payables_turnover = Column(Numeric(10, 4))
    days_sales_outstanding = Column(Numeric(10, 2))
    days_inventory_outstanding = Column(Numeric(10, 2))
    days_payable_outstanding = Column(Numeric(10, 2))
    cash_conversion_cycle = Column(Numeric(10, 2))

    # Market Value Ratios
    pe_ratio = Column(Numeric(10, 4))
    pe_ratio_forward = Column(Numeric(10, 4))
    peg_ratio = Column(Numeric(10, 4))
    pb_ratio = Column(Numeric(10, 4))
    ps_ratio = Column(Numeric(10, 4))
    pcf_ratio = Column(Numeric(10, 4))
    ev_ebitda = Column(Numeric(10, 4))
    ev_sales = Column(Numeric(10, 4))
    ev_fcf = Column(Numeric(10, 4))
    dividend_yield = Column(Numeric(10, 4))
    dividend_payout_ratio = Column(Numeric(10, 4))

    # Growth Ratios
    revenue_growth_yoy = Column(Numeric(10, 4))
    revenue_growth_qoq = Column(Numeric(10, 4))
    eps_growth_yoy = Column(Numeric(10, 4))
    earnings_growth_yoy = Column(Numeric(10, 4))
    sustainable_growth_rate = Column(Numeric(10, 4))

    # Cash Flow Ratios
    operating_cash_flow_margin = Column(Numeric(10, 4))
    free_cash_flow_margin = Column(Numeric(10, 4))
    cash_return_on_assets = Column(Numeric(10, 4))
    fcf_to_net_income = Column(Numeric(10, 4))

    # Relationships
    company = relationship("Company", back_populates="financial_ratios")

    def __repr__(self) -> str:
        return f"<FinancialRatio(company_id={self.company_id}, date={self.calculation_date})>"
