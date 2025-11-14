"""
Company schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CompanyBase(BaseModel):
    """Base company schema with common fields."""

    ticker: str = Field(..., max_length=20, description="Stock ticker symbol")
    name: str = Field(..., max_length=200, description="Company name")
    sector: Optional[str] = Field(None, max_length=100, description="Business sector")
    industry: Optional[str] = Field(None, max_length=100, description="Industry classification")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    country: Optional[str] = Field(None, max_length=50, description="Country of incorporation")
    currency: str = Field("USD", max_length=10, description="Reporting currency")
    exchange: Optional[str] = Field(None, max_length=50, description="Stock exchange")
    fiscal_year_end: Optional[str] = Field(None, max_length=20, description="Fiscal year end (e.g., December)")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, max_length=200, description="Company website URL")
    employees: Optional[int] = Field(None, description="Number of employees")
    founded_year: Optional[int] = Field(None, description="Year company was founded")


class CompanyCreate(CompanyBase):
    """Schema for creating a new company."""

    pass


class CompanyUpdate(BaseModel):
    """Schema for updating an existing company."""

    ticker: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=200)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market_cap: Optional[float] = None
    country: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=10)
    exchange: Optional[str] = Field(None, max_length=50)
    fiscal_year_end: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=200)
    employees: Optional[int] = None
    founded_year: Optional[int] = None


class CompanyResponse(CompanyBase):
    """Schema for company response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """Schema for paginated company list response."""

    total: int
    page: int
    page_size: int
    companies: list[CompanyResponse]
