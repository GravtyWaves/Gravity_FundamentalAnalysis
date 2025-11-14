"""
Financial Ratios API Endpoints.

Provides endpoints for calculating and retrieving financial ratios.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_tenant_id
from app.models.ratios import FinancialRatio
from app.schemas.ratios import FinancialRatioCreate, FinancialRatioResponse
from app.services.ratio_calculation_service import RatioCalculationService
from sqlalchemy import select

router = APIRouter(prefix="/ratios", tags=["ratios"])


@router.post("/calculate", response_model=FinancialRatioResponse, status_code=status.HTTP_201_CREATED)
async def calculate_ratios(
    company_id: UUID,
    period_end_date: date,
    calculation_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Calculate all financial ratios for a company.

    Calculates 48 financial ratios across 7 categories:
    - Liquidity (5 ratios)
    - Profitability (8 ratios)
    - Leverage (6 ratios)
    - Efficiency (9 ratios)
    - Market Value (11 ratios)
    - Growth (5 ratios)
    - Cash Flow (4 ratios)

    **Requirements:**
    - Company must exist
    - Income Statement and Balance Sheet required for period_end_date
    - Cash Flow Statement optional (some ratios will be None if missing)

    **Parameters:**
    - **company_id**: Company UUID
    - **period_end_date**: Period end date of financial statements (YYYY-MM-DD)
    - **calculation_date**: Date of calculation (defaults to today)

    **Returns:**
    - FinancialRatio object with all calculated ratios
    - Ratios that cannot be calculated (e.g., due to missing data) will be None

    **Example:**
    ```json
    {
        "company_id": "123e4567-e89b-12d3-a456-426614174000",
        "period_end_date": "2023-12-31",
        "calculation_date": "2024-01-15"
    }
    ```
    """
    try:
        service = RatioCalculationService(db, tenant_id)
        ratio = await service.calculate_all_ratios(company_id, period_end_date, calculation_date)
        return ratio
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate ratios: {str(e)}",
        )


@router.get("/{company_id}", response_model=List[FinancialRatioResponse])
async def get_company_ratios(
    company_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get historical financial ratios for a company.

    Returns all calculated ratios for the company, ordered by calculation date (newest first).

    **Parameters:**
    - **company_id**: Company UUID
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (1-1000)

    **Returns:**
    - List of FinancialRatio objects

    **Example Response:**
    ```json
    [
        {
            "id": "...",
            "company_id": "...",
            "calculation_date": "2024-01-15",
            "period_end_date": "2023-12-31",
            "current_ratio": 2.5,
            "quick_ratio": 1.5,
            "net_margin": 0.135,
            ...
        }
    ]
    ```
    """
    try:
        result = await db.execute(
            select(FinancialRatio)
            .where(
                FinancialRatio.company_id == company_id,
                FinancialRatio.tenant_id == str(tenant_id),
            )
            .order_by(FinancialRatio.calculation_date.desc())
            .offset(skip)
            .limit(limit)
        )
        ratios = result.scalars().all()
        return ratios
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ratios: {str(e)}",
        )


@router.get("/{company_id}/latest", response_model=FinancialRatioResponse)
async def get_latest_ratios(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get the latest calculated financial ratios for a company.

    Returns the most recent ratio calculation based on calculation_date.

    **Parameters:**
    - **company_id**: Company UUID

    **Returns:**
    - FinancialRatio object with latest ratios
    - HTTP 404 if no ratios found for company

    **Example Response:**
    ```json
    {
        "id": "...",
        "company_id": "...",
        "calculation_date": "2024-01-15",
        "period_end_date": "2023-12-31",
        "current_ratio": 2.5,
        "quick_ratio": 1.5,
        "gross_margin": 0.4,
        "operating_margin": 0.2,
        "net_margin": 0.135,
        "roa": 0.09,
        "roe": 0.16875,
        ...
    }
    ```
    """
    try:
        result = await db.execute(
            select(FinancialRatio)
            .where(
                FinancialRatio.company_id == company_id,
                FinancialRatio.tenant_id == str(tenant_id),
            )
            .order_by(FinancialRatio.calculation_date.desc())
            .limit(1)
        )
        ratio = result.scalar_one_or_none()
        
        if not ratio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No ratios found for company {company_id}",
            )
        
        return ratio
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest ratios: {str(e)}",
        )


@router.delete("/{ratio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ratio(
    ratio_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Delete a financial ratio record.

    **Parameters:**
    - **ratio_id**: FinancialRatio UUID

    **Returns:**
    - HTTP 204 on success
    - HTTP 404 if ratio not found
    """
    try:
        result = await db.execute(
            select(FinancialRatio).where(
                FinancialRatio.id == ratio_id,
                FinancialRatio.tenant_id == str(tenant_id),
            )
        )
        ratio = result.scalar_one_or_none()
        
        if not ratio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ratio {ratio_id} not found",
            )
        
        await db.delete(ratio)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete ratio: {str(e)}",
        )
