"""
Financial statements API endpoints.
"""

from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_tenant_id
from app.schemas.financial_statements import (
    BalanceSheetCreate,
    BalanceSheetResponse,
    CashFlowStatementCreate,
    CashFlowStatementResponse,
    IncomeStatementCreate,
    IncomeStatementResponse,
)
from app.services.financial_statements_service import FinancialStatementsService

router = APIRouter(prefix="/financial-statements", tags=["financial-statements"])


# ==================== Income Statement Endpoints ====================
@router.post("/income-statements", response_model=IncomeStatementResponse, status_code=status.HTTP_201_CREATED)
async def create_income_statement(
    statement_data: IncomeStatementCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new income statement.

    - **company_id**: UUID of the company
    - **fiscal_year**: Fiscal year (e.g., 2023)
    - **fiscal_quarter**: Fiscal quarter (1-4) for quarterly statements
    - **period_type**: "Annual" or "Quarterly"
    - **period_end_date**: End date of the reporting period
    - Revenue, expenses, and other P&L fields
    """
    service = FinancialStatementsService(db, tenant_id)
    statement = await service.create_income_statement(statement_data)
    return IncomeStatementResponse.model_validate(statement)


@router.get("/income-statements/{company_id}", response_model=list[IncomeStatementResponse])
async def get_income_statements(
    company_id: UUID,
    period_type: Optional[Literal["Annual", "Quarterly"]] = Query(None, description="Filter by period type"),
    start_year: Optional[int] = Query(None, description="Start fiscal year"),
    end_year: Optional[int] = Query(None, description="End fiscal year"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Get income statements for a company.

    - **company_id**: UUID of the company
    - **period_type**: Optional filter for Annual or Quarterly statements
    - **start_year**: Optional start fiscal year filter
    - **end_year**: Optional end fiscal year filter
    """
    service = FinancialStatementsService(db, tenant_id)
    statements = await service.get_income_statements(
        company_id=company_id, period_type=period_type, start_year=start_year, end_year=end_year
    )
    return [IncomeStatementResponse.model_validate(s) for s in statements]


# ==================== Balance Sheet Endpoints ====================
@router.post("/balance-sheets", response_model=BalanceSheetResponse, status_code=status.HTTP_201_CREATED)
async def create_balance_sheet(
    statement_data: BalanceSheetCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new balance sheet.

    - **company_id**: UUID of the company
    - **fiscal_year**: Fiscal year
    - **fiscal_quarter**: Fiscal quarter (1-4) for quarterly statements
    - **period_type**: "Annual" or "Quarterly"
    - **period_end_date**: End date of the reporting period
    - Assets, liabilities, and equity fields
    """
    service = FinancialStatementsService(db, tenant_id)
    statement = await service.create_balance_sheet(statement_data)
    return BalanceSheetResponse.model_validate(statement)


@router.get("/balance-sheets/{company_id}", response_model=list[BalanceSheetResponse])
async def get_balance_sheets(
    company_id: UUID,
    period_type: Optional[Literal["Annual", "Quarterly"]] = Query(None, description="Filter by period type"),
    start_year: Optional[int] = Query(None, description="Start fiscal year"),
    end_year: Optional[int] = Query(None, description="End fiscal year"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Get balance sheets for a company.

    - **company_id**: UUID of the company
    - **period_type**: Optional filter for Annual or Quarterly statements
    - **start_year**: Optional start fiscal year filter
    - **end_year**: Optional end fiscal year filter
    """
    service = FinancialStatementsService(db, tenant_id)
    statements = await service.get_balance_sheets(
        company_id=company_id, period_type=period_type, start_year=start_year, end_year=end_year
    )
    return [BalanceSheetResponse.model_validate(s) for s in statements]


# ==================== Cash Flow Statement Endpoints ====================
@router.post("/cash-flow-statements", response_model=CashFlowStatementResponse, status_code=status.HTTP_201_CREATED)
async def create_cash_flow_statement(
    statement_data: CashFlowStatementCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new cash flow statement.

    - **company_id**: UUID of the company
    - **fiscal_year**: Fiscal year
    - **fiscal_quarter**: Fiscal quarter (1-4) for quarterly statements
    - **period_type**: "Annual" or "Quarterly"
    - **period_end_date**: End date of the reporting period
    - Operating, investing, and financing cash flow fields
    """
    service = FinancialStatementsService(db, tenant_id)
    statement = await service.create_cash_flow_statement(statement_data)
    return CashFlowStatementResponse.model_validate(statement)


@router.get("/cash-flow-statements/{company_id}", response_model=list[CashFlowStatementResponse])
async def get_cash_flow_statements(
    company_id: UUID,
    period_type: Optional[Literal["Annual", "Quarterly"]] = Query(None, description="Filter by period type"),
    start_year: Optional[int] = Query(None, description="Start fiscal year"),
    end_year: Optional[int] = Query(None, description="End fiscal year"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """
    Get cash flow statements for a company.

    - **company_id**: UUID of the company
    - **period_type**: Optional filter for Annual or Quarterly statements
    - **start_year**: Optional start fiscal year filter
    - **end_year**: Optional end fiscal year filter
    """
    service = FinancialStatementsService(db, tenant_id)
    statements = await service.get_cash_flow_statements(
        company_id=company_id, period_type=period_type, start_year=start_year, end_year=end_year
    )
    return [CashFlowStatementResponse.model_validate(s) for s in statements]
