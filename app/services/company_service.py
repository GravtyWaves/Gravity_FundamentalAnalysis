"""
Company service layer for business logic.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:
    """Service class for company-related business logic."""

    def __init__(self, db: AsyncSession, tenant_id: UUID | str):
        """
        Initialize company service.

        Args:
            db: Database session
            tenant_id: Current tenant ID for multi-tenancy (UUID or str)
        """
        self.db = db
        # Convert UUID to string for database storage
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        """
        Get company by ID with tenant isolation.

        Args:
            company_id: Company UUID

        Returns:
            Company object or None if not found
        """
        result = await self.db.execute(
            select(Company).where(Company.id == company_id, Company.tenant_id == self.tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ticker(self, ticker: str) -> Optional[Company]:
        """
        Get company by ticker symbol.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Company object or None if not found
        """
        result = await self.db.execute(
            select(Company).where(Company.ticker == ticker.upper(), Company.tenant_id == self.tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_companies(
        self,
        skip: int = 0,
        limit: int = 100,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
    ) -> tuple[list[Company], int]:
        """
        List companies with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            sector: Filter by sector
            industry: Filter by industry
            country: Filter by country

        Returns:
            Tuple of (list of companies, total count)
        """
        query = select(Company).where(Company.tenant_id == self.tenant_id)

        # Apply filters
        if sector:
            query = query.where(Company.sector == sector)
        if industry:
            query = query.where(Company.industry == industry)
        if country:
            query = query.where(Company.country == country)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Company.name)

        # Execute query
        result = await self.db.execute(query)
        companies = result.scalars().all()

        return list(companies), total

    async def create_company(self, company_data: CompanyCreate) -> Company:
        """
        Create a new company.

        Args:
            company_data: Company creation data

        Returns:
            Created company object

        Raises:
            ValueError: If ticker already exists
        """
        # Check if ticker already exists
        existing = await self.get_by_ticker(company_data.ticker)
        if existing:
            raise ValueError(f"Company with ticker {company_data.ticker} already exists")

        # Create company
        company = Company(**company_data.model_dump(), tenant_id=self.tenant_id)

        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)

        return company

    async def update_company(self, company_id: UUID, company_data: CompanyUpdate) -> Optional[Company]:
        """
        Update an existing company.

        Args:
            company_id: Company UUID
            company_data: Company update data

        Returns:
            Updated company object or None if not found

        Raises:
            ValueError: If ticker already exists for another company
        """
        company = await self.get_by_id(company_id)
        if not company:
            return None

        # Check ticker uniqueness if being updated
        if company_data.ticker and company_data.ticker != company.ticker:
            existing = await self.get_by_ticker(company_data.ticker)
            if existing and existing.id != company_id:
                raise ValueError(f"Company with ticker {company_data.ticker} already exists")

        # Update fields
        update_data = company_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(company, field, value)

        await self.db.commit()
        await self.db.refresh(company)

        return company

    async def delete_company(self, company_id: UUID) -> bool:
        """
        Delete a company.

        Args:
            company_id: Company UUID

        Returns:
            True if deleted, False if not found
        """
        company = await self.get_by_id(company_id)
        if not company:
            return False

        await self.db.delete(company)
        await self.db.commit()

        return True

    async def search_companies(self, query: str, limit: int = 20) -> list[Company]:
        """
        Search companies by name or ticker.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching companies
        """
        from sqlalchemy import or_

        search_query = select(Company).where(
            Company.tenant_id == self.tenant_id,
            or_(
                Company.ticker.ilike(f"%{query}%"),
                Company.name.ilike(f"%{query}%"),
            ),
        )

        search_query = search_query.limit(limit).order_by(Company.name)

        result = await self.db.execute(search_query)
        return list(result.scalars().all())
