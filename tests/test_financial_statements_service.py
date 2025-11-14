"""
Tests for Financial Statements Service.

Comprehensive tests for income statements, balance sheets, and cash flow statements.
"""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.models.company import Company
from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
from app.services.financial_statements_service import FinancialStatementsService


@pytest.fixture
async def test_company(test_db, test_tenant_id):
    """Create a test company."""
    company = Company(
        id=uuid4(),
        tenant_id=test_tenant_id,
        ticker="TEST",
        name="Test Company",
        exchange="TSE",
        sector="Technology",
        industry="Software",
    )
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    return company


class TestIncomeStatementCRUD:
    """Test CRUD operations for income statements."""
    
    @pytest.mark.asyncio
    async def test_create_income_statement(self, test_db, test_company, test_tenant_id):
        """Test creating an income statement."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        data = {
            "company_id": test_company.id,
            "period_end_date": date(2024, 12, 31),
            "period_type": "annual",
            "fiscal_year": 2024,
            "revenue": Decimal("1000000"),
            "cost_of_revenue": Decimal("400000"),
            "gross_profit": Decimal("600000"),
            "operating_expenses": Decimal("300000"),
            "operating_income": Decimal("300000"),
            "net_income": Decimal("250000"),
            "ebitda": Decimal("350000"),
            "eps_basic": Decimal("10.00"),
            "eps_diluted": Decimal("9.50"),
        }
        
        stmt = await service.create_income_statement(**data)
        
        assert stmt.id is not None
        assert stmt.company_id == test_company.id
        assert stmt.revenue == Decimal("1000000")
        assert stmt.net_income == Decimal("250000")
        assert stmt.ebitda == Decimal("350000")
    
    @pytest.mark.asyncio
    async def test_get_income_statement_by_id(self, test_db, test_company, test_tenant_id):
        """Test retrieving income statement by ID."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        stmt = IncomeStatement(
            id=uuid4(),
            tenant_id=test_tenant_id,
            company_id=test_company.id,
            period_end_date=date(2024, 12, 31),
            period_type="annual",
            fiscal_year=2024,
            revenue=Decimal("1000000"),
            net_income=Decimal("250000"),
        )
        test_db.add(stmt)
        await test_db.commit()
        await test_db.refresh(stmt)
        
        retrieved = await service.get_income_statement(stmt.id)
        
        assert retrieved is not None
        assert retrieved.id == stmt.id
        assert retrieved.revenue == Decimal("1000000")
    
    @pytest.mark.asyncio
    async def test_get_company_income_statements(self, test_db, test_company, test_tenant_id):
        """Test retrieving all income statements for a company."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        # Create multiple statements
        for year in [2022, 2023, 2024]:
            stmt = IncomeStatement(
                id=uuid4(),
                tenant_id=test_tenant_id,
                company_id=test_company.id,
                period_end_date=date(year, 12, 31),
                period_type="annual",
                fiscal_year=year,
                revenue=Decimal(f"{1000000 + year * 100000}"),
                net_income=Decimal(f"{250000 + year * 25000}"),
            )
            test_db.add(stmt)
        await test_db.commit()
        
        statements = await service.get_company_income_statements(test_company.id)
        
        assert len(statements) == 3
        # Should be ordered by date descending
        assert statements[0].fiscal_year == 2024
        assert statements[2].fiscal_year == 2022


class TestBalanceSheetCRUD:
    """Test CRUD operations for balance sheets."""
    
    @pytest.mark.asyncio
    async def test_create_balance_sheet(self, test_db, test_company, test_tenant_id):
        """Test creating a balance sheet."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        data = {
            "company_id": test_company.id,
            "period_end_date": date(2024, 12, 31),
            "period_type": "annual",
            "fiscal_year": 2024,
            "total_assets": Decimal("5000000"),
            "current_assets": Decimal("2000000"),
            "cash_and_equivalents": Decimal("500000"),
            "total_liabilities": Decimal("3000000"),
            "current_liabilities": Decimal("800000"),
            "stockholders_equity": Decimal("2000000"),
        }
        
        stmt = await service.create_balance_sheet(**data)
        
        assert stmt.id is not None
        assert stmt.total_assets == Decimal("5000000")
        assert stmt.stockholders_equity == Decimal("2000000")
    
    @pytest.mark.asyncio
    async def test_balance_sheet_validation(self, test_db, test_company, test_tenant_id):
        """Test balance sheet equation: Assets = Liabilities + Equity."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        data = {
            "company_id": test_company.id,
            "period_end_date": date(2024, 12, 31),
            "period_type": "annual",
            "fiscal_year": 2024,
            "total_assets": Decimal("5000000"),
            "total_liabilities": Decimal("3000000"),
            "stockholders_equity": Decimal("2000000"),
        }
        
        stmt = await service.create_balance_sheet(**data)
        
        # Verify accounting equation
        assert stmt.total_assets == stmt.total_liabilities + stmt.stockholders_equity


class TestCashFlowStatementCRUD:
    """Test CRUD operations for cash flow statements."""
    
    @pytest.mark.asyncio
    async def test_create_cash_flow_statement(self, test_db, test_company, test_tenant_id):
        """Test creating a cash flow statement."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        data = {
            "company_id": test_company.id,
            "period_end_date": date(2024, 12, 31),
            "period_type": "annual",
            "fiscal_year": 2024,
            "operating_cash_flow": Decimal("280000"),
            "investing_cash_flow": Decimal("-150000"),
            "financing_cash_flow": Decimal("-50000"),
            "free_cash_flow": Decimal("200000"),
            "capital_expenditures": Decimal("80000"),
        }
        
        stmt = await service.create_cash_flow_statement(**data)
        
        assert stmt.id is not None
        assert stmt.operating_cash_flow == Decimal("280000")
        assert stmt.free_cash_flow == Decimal("200000")
    
    @pytest.mark.asyncio
    async def test_cash_flow_net_change(self, test_db, test_company, test_tenant_id):
        """Test net cash flow calculation."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        data = {
            "company_id": test_company.id,
            "period_end_date": date(2024, 12, 31),
            "period_type": "annual",
            "fiscal_year": 2024,
            "operating_cash_flow": Decimal("280000"),
            "investing_cash_flow": Decimal("-150000"),
            "financing_cash_flow": Decimal("-50000"),
        }
        
        stmt = await service.create_cash_flow_statement(**data)
        
        # Net change = Operating + Investing + Financing
        net_change = stmt.operating_cash_flow + stmt.investing_cash_flow + stmt.financing_cash_flow
        assert net_change == Decimal("80000")


class TestFinancialStatementsFiltering:
    """Test filtering and querying financial statements."""
    
    @pytest.mark.asyncio
    async def test_filter_by_fiscal_year(self, test_db, test_company, test_tenant_id):
        """Test filtering statements by fiscal year."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        # Create statements for multiple years
        for year in [2022, 2023, 2024]:
            stmt = IncomeStatement(
                id=uuid4(),
                tenant_id=test_tenant_id,
                company_id=test_company.id,
                period_end_date=date(year, 12, 31),
                period_type="annual",
                fiscal_year=year,
                revenue=Decimal("1000000"),
                net_income=Decimal("250000"),
            )
            test_db.add(stmt)
        await test_db.commit()
        
        # Filter for 2024
        statements = await service.get_company_income_statements(
            test_company.id,
            fiscal_year=2024
        )
        
        assert len(statements) == 1
        assert statements[0].fiscal_year == 2024
    
    @pytest.mark.asyncio
    async def test_filter_by_period_type(self, test_db, test_company, test_tenant_id):
        """Test filtering by annual vs quarterly."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        # Create annual statement
        annual = IncomeStatement(
            id=uuid4(),
            tenant_id=test_tenant_id,
            company_id=test_company.id,
            period_end_date=date(2024, 12, 31),
            period_type="annual",
            fiscal_year=2024,
            revenue=Decimal("1000000"),
            net_income=Decimal("250000"),
        )
        test_db.add(annual)
        
        # Create quarterly statements
        for quarter in [1, 2, 3, 4]:
            stmt = IncomeStatement(
                id=uuid4(),
                tenant_id=test_tenant_id,
                company_id=test_company.id,
                period_end_date=date(2024, quarter * 3, 1),
                period_type="quarterly",
                fiscal_year=2024,
                fiscal_quarter=quarter,
                revenue=Decimal("250000"),
                net_income=Decimal("62500"),
            )
            test_db.add(stmt)
        await test_db.commit()
        
        # Filter annual only
        annual_statements = await service.get_company_income_statements(
            test_company.id,
            period_type="annual"
        )
        assert len(annual_statements) == 1
        
        # Filter quarterly only
        quarterly_statements = await service.get_company_income_statements(
            test_company.id,
            period_type="quarterly"
        )
        assert len(quarterly_statements) == 4


class TestFinancialStatementsDeletion:
    """Test deletion operations."""
    
    @pytest.mark.asyncio
    async def test_delete_income_statement(self, test_db, test_company, test_tenant_id):
        """Test deleting an income statement."""
        service = FinancialStatementsService(test_db, test_tenant_id)
        
        stmt = IncomeStatement(
            id=uuid4(),
            tenant_id=test_tenant_id,
            company_id=test_company.id,
            period_end_date=date(2024, 12, 31),
            period_type="annual",
            fiscal_year=2024,
            revenue=Decimal("1000000"),
            net_income=Decimal("250000"),
        )
        test_db.add(stmt)
        await test_db.commit()
        
        stmt_id = stmt.id
        
        # Delete
        await service.delete_income_statement(stmt_id)
        
        # Verify deletion
        deleted = await service.get_income_statement(stmt_id)
        assert deleted is None


class TestTenantIsolation:
    """Test multi-tenancy isolation."""
    
    @pytest.mark.asyncio
    async def test_tenant_isolation_income_statements(self, test_db, test_company):
        """Test that tenants cannot access each other's data."""
        tenant1_id = "tenant-1"
        tenant2_id = "tenant-2"
        
        # Create statement for tenant 1
        stmt1 = IncomeStatement(
            id=uuid4(),
            tenant_id=tenant1_id,
            company_id=test_company.id,
            period_end_date=date(2024, 12, 31),
            period_type="annual",
            fiscal_year=2024,
            revenue=Decimal("1000000"),
            net_income=Decimal("250000"),
        )
        test_db.add(stmt1)
        await test_db.commit()
        
        # Service for tenant 2 should not see tenant 1's data
        service2 = FinancialStatementsService(test_db, tenant2_id)
        statements = await service2.get_company_income_statements(test_company.id)
        
        assert len(statements) == 0
