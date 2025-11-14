"""
Unit tests for Company service.
"""

import pytest
from uuid import uuid4

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company_service import CompanyService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_company(test_db, test_tenant_id):
    """Test creating a new company."""
    service = CompanyService(test_db, uuid4())

    company_data = CompanyCreate(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        market_cap=3000000000000.0,
        country="USA",
        currency="USD",
        exchange="NASDAQ",
    )

    company = await service.create_company(company_data)

    assert company.id is not None
    assert company.ticker == "AAPL"
    assert company.name == "Apple Inc."
    assert company.sector == "Technology"
    assert company.tenant_id == service.tenant_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_duplicate_ticker(test_db, test_tenant_id):
    """Test that creating a company with duplicate ticker raises error."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    company_data = CompanyCreate(ticker="MSFT", name="Microsoft Corporation")

    # Create first company
    await service.create_company(company_data)

    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        await service.create_company(company_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_id(test_db, test_tenant_id):
    """Test getting a company by ID."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    company_data = CompanyCreate(ticker="GOOGL", name="Alphabet Inc.")
    created = await service.create_company(company_data)

    # Retrieve by ID
    retrieved = await service.get_by_id(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.ticker == "GOOGL"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_ticker(test_db, test_tenant_id):
    """Test getting a company by ticker."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    company_data = CompanyCreate(ticker="TSLA", name="Tesla Inc.")
    await service.create_company(company_data)

    # Retrieve by ticker
    retrieved = await service.get_by_ticker("TSLA")

    assert retrieved is not None
    assert retrieved.ticker == "TSLA"
    assert retrieved.name == "Tesla Inc."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_companies(test_db, test_tenant_id):
    """Test listing companies with pagination."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    # Create multiple companies
    for i in range(5):
        company_data = CompanyCreate(ticker=f"TEST{i}", name=f"Test Company {i}", sector="Technology")
        await service.create_company(company_data)

    # List all companies
    companies, total = await service.list_companies(skip=0, limit=10)

    assert len(companies) == 5
    assert total == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_companies_with_filter(test_db, test_tenant_id):
    """Test listing companies with sector filter."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    # Create companies in different sectors
    await service.create_company(CompanyCreate(ticker="TECH1", name="Tech Company 1", sector="Technology"))
    await service.create_company(CompanyCreate(ticker="TECH2", name="Tech Company 2", sector="Technology"))
    await service.create_company(CompanyCreate(ticker="FIN1", name="Finance Company 1", sector="Finance"))

    # Filter by Technology sector
    companies, total = await service.list_companies(skip=0, limit=10, sector="Technology")

    assert len(companies) == 2
    assert total == 2
    assert all(c.sector == "Technology" for c in companies)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_company(test_db, test_tenant_id):
    """Test updating a company."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    company_data = CompanyCreate(ticker="AMZN", name="Amazon.com Inc.")
    created = await service.create_company(company_data)

    # Update company
    update_data = CompanyUpdate(market_cap=1500000000000.0, employees=1500000)
    updated = await service.update_company(created.id, update_data)

    assert updated is not None
    assert updated.market_cap == 1500000000000.0
    assert updated.employees == 1500000
    assert updated.ticker == "AMZN"  # Unchanged field


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_company(test_db, test_tenant_id):
    """Test deleting a company."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    company_data = CompanyCreate(ticker="FB", name="Meta Platforms Inc.")
    created = await service.create_company(company_data)

    # Delete company
    deleted = await service.delete_company(created.id)
    assert deleted is True

    # Verify deletion
    retrieved = await service.get_by_id(created.id)
    assert retrieved is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_companies(test_db, test_tenant_id):
    """Test searching companies by name or ticker."""
    tenant_id = uuid4()
    service = CompanyService(test_db, tenant_id)

    # Create companies
    await service.create_company(CompanyCreate(ticker="NFLX", name="Netflix Inc."))
    await service.create_company(CompanyCreate(ticker="NVDA", name="NVIDIA Corporation"))
    await service.create_company(CompanyCreate(ticker="AMD", name="Advanced Micro Devices Inc."))

    # Search by partial name
    results = await service.search_companies("Net", limit=10)
    assert len(results) == 1
    assert results[0].ticker == "NFLX"

    # Search by partial ticker
    results = await service.search_companies("NV", limit=10)
    assert len(results) == 1
    assert results[0].ticker == "NVDA"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tenant_isolation(test_db):
    """Test that companies are isolated by tenant."""
    tenant1_id = uuid4()
    tenant2_id = uuid4()

    service1 = CompanyService(test_db, tenant1_id)
    service2 = CompanyService(test_db, tenant2_id)

    # Create company for tenant 1
    company_data = CompanyCreate(ticker="ISOLATED", name="Isolated Company")
    await service1.create_company(company_data)

    # Tenant 2 should not see tenant 1's company
    retrieved = await service2.get_by_ticker("ISOLATED")
    assert retrieved is None

    # Tenant 1 should see their own company
    retrieved = await service1.get_by_ticker("ISOLATED")
    assert retrieved is not None
