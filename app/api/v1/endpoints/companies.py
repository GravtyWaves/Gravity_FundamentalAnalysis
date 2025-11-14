"""
Company API endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_tenant_id
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    List companies with pagination and filtering.

    - **page**: Page number (starting from 1)
    - **page_size**: Number of items per page (max 100)
    - **sector**: Optional sector filter
    - **industry**: Optional industry filter
    - **country**: Optional country filter
    """
    service = CompanyService(db, tenant_id)

    skip = (page - 1) * page_size
    companies, total = await service.list_companies(
        skip=skip, limit=page_size, sector=sector, industry=industry, country=country
    )

    return CompanyListResponse(
        total=total,
        page=page,
        page_size=page_size,
        companies=[CompanyResponse.model_validate(c) for c in companies],
    )


@router.get("/search", response_model=list[CompanyResponse])
async def search_companies(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Search companies by name or ticker symbol.

    - **q**: Search query (matches ticker or company name)
    - **limit**: Maximum number of results (default 20)
    """
    service = CompanyService(db, tenant_id)
    companies = await service.search_companies(query=q, limit=limit)

    return [CompanyResponse.model_validate(c) for c in companies]


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Get a specific company by ID.

    - **company_id**: UUID of the company
    """
    service = CompanyService(db, tenant_id)
    company = await service.get_by_id(company_id)

    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    return CompanyResponse.model_validate(company)


@router.get("/ticker/{ticker}", response_model=CompanyResponse)
async def get_company_by_ticker(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Get a company by ticker symbol.

    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)
    """
    service = CompanyService(db, tenant_id)
    company = await service.get_by_ticker(ticker)

    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Company with ticker {ticker} not found")

    return CompanyResponse.model_validate(company)


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new company.

    - **ticker**: Stock ticker symbol (required, unique)
    - **name**: Company name (required)
    - **sector**: Business sector (optional)
    - **industry**: Industry classification (optional)
    - Additional fields as per CompanyCreate schema
    """
    service = CompanyService(db, tenant_id)

    try:
        company = await service.create_company(company_data)
        return CompanyResponse.model_validate(company)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company_data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Update an existing company.

    - **company_id**: UUID of the company to update
    - All fields are optional in the update request
    """
    service = CompanyService(db, tenant_id)

    try:
        company = await service.update_company(company_id, company_data)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        return CompanyResponse.model_validate(company)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a company.

    - **company_id**: UUID of the company to delete
    - Note: This will also delete all related financial data (cascade delete)
    """
    service = CompanyService(db, tenant_id)
    deleted = await service.delete_company(company_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    return None
