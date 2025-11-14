"""
Valuation API Endpoints.

Provides endpoints for company valuations using multiple methods:
- DCF (Discounted Cash Flow)
- Comparables (Relative Valuation)
- Asset-Based
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_tenant_id
from app.models.valuation_risk import Valuation
from app.schemas.valuation_risk import ValuationCreate, ValuationResponse
from app.services.valuation_service import ValuationService
from sqlalchemy import select

router = APIRouter(prefix="/valuations", tags=["valuations"])


@router.post("/dcf", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def dcf_valuation(
    company_id: UUID,
    valuation_date: date = Query(..., description="Valuation date (YYYY-MM-DD)"),
    projection_years: int = Query(5, ge=1, le=10, description="Number of projection years (1-10)"),
    perpetual_growth_rate: Decimal = Query(Decimal("0.025"), ge=0, le=0.1, description="Perpetual growth rate (0-10%)"),
    cost_of_equity: Optional[Decimal] = Query(None, ge=0, le=1, description="Cost of equity (optional, auto-estimated if None)"),
    cost_of_debt: Optional[Decimal] = Query(None, ge=0, le=1, description="Cost of debt (optional, auto-estimated if None)"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Perform DCF (Discounted Cash Flow) Valuation.

    **Methodology:**
    1. Calculate WACC (Weighted Average Cost of Capital)
    2. Project Free Cash Flows for specified years
    3. Calculate Terminal Value using Gordon Growth Model
    4. Discount all cash flows to present value
    5. Enterprise Value = PV(FCF) + PV(Terminal Value)
    6. Equity Value = EV - Net Debt
    7. Fair Value per Share = Equity Value / Shares Outstanding

    **Parameters:**
    - **company_id**: Company UUID
    - **valuation_date**: Date of valuation
    - **projection_years**: Years to project (default: 5, max: 10)
    - **perpetual_growth_rate**: Long-term growth rate (default: 2.5%)
    - **cost_of_equity**: Cost of equity (optional, will estimate using CAPM)
    - **cost_of_debt**: Cost of debt (optional, will estimate from interest expense)

    **Returns:**
    - Valuation object with:
        - fair_value_per_share
        - enterprise_value
        - equity_value
        - upside_downside_percent
        - assumptions (WACC, growth rates, etc.)
        - parameters (projected FCF, terminal value, etc.)

    **Example Request:**
    ```
    POST /api/v1/valuations/dcf?company_id=123&valuation_date=2024-01-15&projection_years=5&perpetual_growth_rate=0.025
    ```

    **Example Response:**
    ```json
    {
        "id": "...",
        "company_id": "...",
        "valuation_date": "2024-01-15",
        "method": "DCF",
        "fair_value_per_share": 125.50,
        "current_price": 100.00,
        "upside_downside_percent": 25.50,
        "enterprise_value": 1500000.00,
        "equity_value": 1250000.00,
        "assumptions": {
            "wacc": 0.105,
            "cost_of_equity": 0.15,
            "cost_of_debt": 0.08
        },
        "parameters": {
            "projection_years": 5,
            "perpetual_growth_rate": 0.025,
            "projected_fcf": [110000, 121000, 133100, 146410, 161051],
            "terminal_value": 1650000
        }
    }
    ```
    """
    try:
        service = ValuationService(db, tenant_id)
        valuation = await service.dcf_valuation(
            company_id=company_id,
            valuation_date=valuation_date,
            projection_years=projection_years,
            perpetual_growth_rate=perpetual_growth_rate,
            cost_of_equity=cost_of_equity,
            cost_of_debt=cost_of_debt,
        )
        return valuation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DCF valuation failed: {str(e)}",
        )


@router.post("/comparables", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def comparables_valuation(
    company_id: UUID,
    valuation_date: date = Query(..., description="Valuation date (YYYY-MM-DD)"),
    peer_pe_ratio: Optional[Decimal] = Query(None, description="Industry average P/E ratio"),
    peer_pb_ratio: Optional[Decimal] = Query(None, description="Industry average P/B ratio"),
    peer_ev_ebitda: Optional[Decimal] = Query(None, description="Industry average EV/EBITDA"),
    peer_ev_revenue: Optional[Decimal] = Query(None, description="Industry average EV/Revenue"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Perform Comparables (Relative) Valuation using industry multiples.

    **Methodology:**
    1. P/E Multiple: Fair Value = EPS × Industry P/E
    2. P/B Multiple: Fair Value = Book Value per Share × Industry P/B
    3. EV/EBITDA Multiple: EV = EBITDA × Industry EV/EBITDA → Fair Value
    4. EV/Revenue Multiple: EV = Revenue × Industry EV/Revenue → Fair Value
    5. Weighted Average of all applicable methods

    **Parameters:**
    - **company_id**: Company UUID
    - **valuation_date**: Date of valuation
    - **peer_pe_ratio**: Industry P/E (optional, defaults to 15.0)
    - **peer_pb_ratio**: Industry P/B (optional, defaults to 2.0)
    - **peer_ev_ebitda**: Industry EV/EBITDA (optional, defaults to 10.0)
    - **peer_ev_revenue**: Industry EV/Revenue (optional, defaults to 1.5)

    **Returns:**
    - Valuation object with fair value from weighted average of multiples

    **Example Request:**
    ```
    POST /api/v1/valuations/comparables?company_id=123&valuation_date=2024-01-15&peer_pe_ratio=18&peer_pb_ratio=2.5
    ```

    **Example Response:**
    ```json
    {
        "id": "...",
        "company_id": "...",
        "valuation_date": "2024-01-15",
        "method": "Comparables",
        "fair_value_per_share": 115.75,
        "current_price": 100.00,
        "upside_downside_percent": 15.75,
        "assumptions": {
            "peer_multiples": {
                "pe_ratio": 18.0,
                "pb_ratio": 2.5,
                "ev_to_ebitda": 10.0,
                "ev_to_revenue": 1.5
            }
        },
        "parameters": {
            "methods_used": ["pe_ratio", "pb_ratio", "ev_to_ebitda"],
            "valuations_by_method": {
                "pe_multiple": 120.0,
                "pb_multiple": 110.0,
                "ev_ebitda_multiple": 117.5
            },
            "weights": {
                "pe_multiple": 0.3,
                "pb_multiple": 0.25,
                "ev_ebitda_multiple": 0.45
            }
        }
    }
    ```
    """
    try:
        # Build peer multiples dict
        peer_multiples = {}
        if peer_pe_ratio is not None:
            peer_multiples["pe_ratio"] = peer_pe_ratio
        if peer_pb_ratio is not None:
            peer_multiples["pb_ratio"] = peer_pb_ratio
        if peer_ev_ebitda is not None:
            peer_multiples["ev_to_ebitda"] = peer_ev_ebitda
        if peer_ev_revenue is not None:
            peer_multiples["ev_to_revenue"] = peer_ev_revenue

        service = ValuationService(db, tenant_id)
        valuation = await service.comparables_valuation(
            company_id=company_id,
            valuation_date=valuation_date,
            peer_multiples=peer_multiples if peer_multiples else None,
        )
        return valuation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparables valuation failed: {str(e)}",
        )


@router.post("/asset-based", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def asset_based_valuation(
    company_id: UUID,
    valuation_date: date = Query(..., description="Valuation date (YYYY-MM-DD)"),
    inventory_adjustment: Decimal = Query(Decimal("0.8"), ge=0, le=2, description="Inventory adjustment factor (default: 0.8 = 80% of book)"),
    receivables_adjustment: Decimal = Query(Decimal("0.9"), ge=0, le=2, description="Receivables adjustment factor (default: 0.9 = 90% collectible)"),
    ppe_adjustment: Decimal = Query(Decimal("1.0"), ge=0, le=2, description="PP&E adjustment factor (default: 1.0 = book value)"),
    intangible_adjustment: Decimal = Query(Decimal("0.5"), ge=0, le=2, description="Intangible adjustment factor (default: 0.5 = 50% discount)"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Perform Asset-Based Valuation.

    **Methodology:**
    1. Start with book value of equity
    2. Adjust assets for:
        - Inventory (liquidity discount)
        - Receivables (collectibility)
        - PP&E (replacement cost)
        - Intangibles (heavy discount)
    3. Calculate Adjusted Equity Value
    4. Fair Value per Share = Adjusted Equity / Shares Outstanding

    **Parameters:**
    - **company_id**: Company UUID
    - **valuation_date**: Date of valuation
    - **inventory_adjustment**: Inventory factor (0.8 = 80% of book value)
    - **receivables_adjustment**: Receivables factor (0.9 = 90% collectible)
    - **ppe_adjustment**: PP&E factor (1.0 = book value, 1.1 = 10% premium)
    - **intangible_adjustment**: Intangibles factor (0.5 = 50% discount)

    **Returns:**
    - Valuation object with adjusted asset-based fair value

    **Example Request:**
    ```
    POST /api/v1/valuations/asset-based?company_id=123&valuation_date=2024-01-15&inventory_adjustment=0.75
    ```

    **Example Response:**
    ```json
    {
        "id": "...",
        "company_id": "...",
        "valuation_date": "2024-01-15",
        "method": "Asset-Based",
        "fair_value_per_share": 85.50,
        "current_price": 100.00,
        "upside_downside_percent": -14.50,
        "equity_value": 855000.00,
        "assumptions": {
            "adjustment_factors": {
                "inventory_adjustment": 0.75,
                "receivables_adjustment": 0.9,
                "ppe_adjustment": 1.0,
                "intangible_adjustment": 0.5
            }
        },
        "parameters": {
            "book_value": 800000.00,
            "adjusted_equity": 855000.00,
            "adjusted_assets": 1255000.00
        }
    }
    ```
    """
    try:
        adjustment_factors = {
            "inventory_adjustment": inventory_adjustment,
            "receivables_adjustment": receivables_adjustment,
            "ppe_adjustment": ppe_adjustment,
            "intangible_adjustment": intangible_adjustment,
            "tangible_asset_adjustment": Decimal("1.0"),
        }

        service = ValuationService(db, tenant_id)
        valuation = await service.asset_based_valuation(
            company_id=company_id,
            valuation_date=valuation_date,
            adjustment_factors=adjustment_factors,
        )
        return valuation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Asset-based valuation failed: {str(e)}",
        )


@router.get("/{company_id}", response_model=List[ValuationResponse])
async def get_company_valuations(
    company_id: UUID,
    method: Optional[str] = Query(None, description="Filter by valuation method (DCF, Comparables, Asset-Based)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get historical valuations for a company.

    **Parameters:**
    - **company_id**: Company UUID
    - **method**: Filter by valuation method (optional)
    - **skip**: Pagination offset
    - **limit**: Max results (1-1000)

    **Returns:**
    - List of Valuation objects ordered by date (newest first)
    """
    try:
        query = select(Valuation).where(
            Valuation.company_id == company_id,
            Valuation.tenant_id == str(tenant_id),
        )
        
        if method:
            query = query.where(Valuation.method == method)
        
        query = query.order_by(Valuation.valuation_date.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        valuations = result.scalars().all()
        return valuations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve valuations: {str(e)}",
        )


@router.get("/{company_id}/latest", response_model=ValuationResponse)
async def get_latest_valuation(
    company_id: UUID,
    method: Optional[str] = Query(None, description="Filter by valuation method"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Get the latest valuation for a company.

    **Parameters:**
    - **company_id**: Company UUID
    - **method**: Filter by method (optional)

    **Returns:**
    - Latest Valuation object
    - HTTP 404 if no valuations found
    """
    try:
        query = select(Valuation).where(
            Valuation.company_id == company_id,
            Valuation.tenant_id == str(tenant_id),
        )
        
        if method:
            query = query.where(Valuation.method == method)
        
        query = query.order_by(Valuation.valuation_date.desc()).limit(1)
        
        result = await db.execute(query)
        valuation = result.scalar_one_or_none()
        
        if not valuation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No valuations found for company {company_id}",
            )
        
        return valuation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest valuation: {str(e)}",
        )


@router.delete("/{valuation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_valuation(
    valuation_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Delete a valuation record.

    **Parameters:**
    - **valuation_id**: Valuation UUID

    **Returns:**
    - HTTP 204 on success
    - HTTP 404 if not found
    """
    try:
        result = await db.execute(
            select(Valuation).where(
                Valuation.id == valuation_id,
                Valuation.tenant_id == str(tenant_id),
            )
        )
        valuation = result.scalar_one_or_none()
        
        if not valuation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Valuation {valuation_id} not found",
            )
        
        await db.delete(valuation)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete valuation: {str(e)}",
        )
