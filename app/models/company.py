"""
Company model for storing company information.

Represents publicly traded companies with their basic information.
"""

from sqlalchemy import Column, Date, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Company(BaseModel):
    """
    Company model representing a publicly traded company.

    Attributes:
        ticker: Stock ticker symbol (e.g., AAPL, MSFT)
        name: Full company name
        sector: Business sector (e.g., Technology, Healthcare)
        industry: Specific industry within sector
        market_cap: Market capitalization in USD
        country: Country of incorporation
        currency: Trading currency (e.g., USD, EUR)
        exchange: Stock exchange (e.g., NASDAQ, NYSE)
        fiscal_year_end: Fiscal year end date
        description: Company description
        website: Company website URL
        employees: Number of employees
        founded_year: Year company was founded
    """

    __tablename__ = "companies"

    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), index=True)
    industry = Column(String(100), index=True)
    market_cap = Column(Numeric(20, 2))
    country = Column(String(50))
    currency = Column(String(3), default="USD")
    exchange = Column(String(20))
    fiscal_year_end = Column(Date)
    description = Column(Text)
    website = Column(String(255))
    employees = Column(Numeric(10, 0))
    founded_year = Column(Numeric(4, 0))

    # Relationships
    income_statements = relationship("IncomeStatement", back_populates="company", cascade="all, delete-orphan")
    balance_sheets = relationship("BalanceSheet", back_populates="company", cascade="all, delete-orphan")
    cash_flow_statements = relationship("CashFlowStatement", back_populates="company", cascade="all, delete-orphan")
    financial_ratios = relationship("FinancialRatio", back_populates="company", cascade="all, delete-orphan")
    valuations = relationship("Valuation", back_populates="company", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="company", cascade="all, delete-orphan")
    market_data = relationship("MarketData", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of company."""
        return f"<Company(ticker={self.ticker}, name={self.name})>"
