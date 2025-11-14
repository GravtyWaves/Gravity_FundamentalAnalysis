"""
Financial statements service layer.
"""

from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
from app.schemas.financial_statements import (
    BalanceSheetCreate,
    CashFlowStatementCreate,
    IncomeStatementCreate,
)


class FinancialStatementsService:
    """Service class for financial statements business logic."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        """
        Initialize financial statements service.

        Args:
            db: Database session
            tenant_id: Current tenant ID for multi-tenancy
        """
        self.db = db
        # Convert UUID to string for database storage
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id
        self.tenant_id = tenant_id

    # ==================== Income Statement ====================
    async def create_income_statement(self, statement_data: IncomeStatementCreate) -> IncomeStatement:
        """
        Create a new income statement.

        Args:
            statement_data: Income statement creation data

        Returns:
            Created income statement object
        """
        statement = IncomeStatement(**statement_data.model_dump(), tenant_id=self.tenant_id)

        self.db.add(statement)
        await self.db.commit()
        await self.db.refresh(statement)

        return statement

    async def get_income_statements(
        self,
        company_id: UUID,
        period_type: Optional[Literal["Annual", "Quarterly"]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> list[IncomeStatement]:
        """
        Get income statements for a company with filters.

        Args:
            company_id: Company UUID
            period_type: Filter by Annual or Quarterly
            start_year: Start fiscal year
            end_year: End fiscal year

        Returns:
            List of income statements
        """
        query = select(IncomeStatement).where(
            IncomeStatement.company_id == company_id, IncomeStatement.tenant_id == self.tenant_id
        )

        if period_type:
            query = query.where(IncomeStatement.period_type == period_type)
        if start_year:
            query = query.where(IncomeStatement.fiscal_year >= start_year)
        if end_year:
            query = query.where(IncomeStatement.fiscal_year <= end_year)

        query = query.order_by(IncomeStatement.fiscal_year.desc(), IncomeStatement.fiscal_quarter.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Balance Sheet ====================
    async def create_balance_sheet(self, statement_data: BalanceSheetCreate) -> BalanceSheet:
        """
        Create a new balance sheet.

        Args:
            statement_data: Balance sheet creation data

        Returns:
            Created balance sheet object
        """
        statement = BalanceSheet(**statement_data.model_dump(), tenant_id=self.tenant_id)

        self.db.add(statement)
        await self.db.commit()
        await self.db.refresh(statement)

        return statement

    async def get_balance_sheets(
        self,
        company_id: UUID,
        period_type: Optional[Literal["Annual", "Quarterly"]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> list[BalanceSheet]:
        """
        Get balance sheets for a company with filters.

        Args:
            company_id: Company UUID
            period_type: Filter by Annual or Quarterly
            start_year: Start fiscal year
            end_year: End fiscal year

        Returns:
            List of balance sheets
        """
        query = select(BalanceSheet).where(
            BalanceSheet.company_id == company_id, BalanceSheet.tenant_id == self.tenant_id
        )

        if period_type:
            query = query.where(BalanceSheet.period_type == period_type)
        if start_year:
            query = query.where(BalanceSheet.fiscal_year >= start_year)
        if end_year:
            query = query.where(BalanceSheet.fiscal_year <= end_year)

        query = query.order_by(BalanceSheet.fiscal_year.desc(), BalanceSheet.fiscal_quarter.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Cash Flow Statement ====================
    async def create_cash_flow_statement(self, statement_data: CashFlowStatementCreate) -> CashFlowStatement:
        """
        Create a new cash flow statement.

        Args:
            statement_data: Cash flow statement creation data

        Returns:
            Created cash flow statement object
        """
        statement = CashFlowStatement(**statement_data.model_dump(), tenant_id=self.tenant_id)

        self.db.add(statement)
        await self.db.commit()
        await self.db.refresh(statement)

        return statement

    async def get_cash_flow_statements(
        self,
        company_id: UUID,
        period_type: Optional[Literal["Annual", "Quarterly"]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> list[CashFlowStatement]:
        """
        Get cash flow statements for a company with filters.

        Args:
            company_id: Company UUID
            period_type: Filter by Annual or Quarterly
            start_year: Start fiscal year
            end_year: End fiscal year

        Returns:
            List of cash flow statements
        """
        query = select(CashFlowStatement).where(
            CashFlowStatement.company_id == company_id, CashFlowStatement.tenant_id == self.tenant_id
        )

        if period_type:
            query = query.where(CashFlowStatement.period_type == period_type)
        if start_year:
            query = query.where(CashFlowStatement.fiscal_year >= start_year)
        if end_year:
            query = query.where(CashFlowStatement.fiscal_year <= end_year)

        query = query.order_by(CashFlowStatement.fiscal_year.desc(), CashFlowStatement.fiscal_quarter.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())
