"""
Data Integration Service.

Integrates with Data Collection microservice to fetch and store financial data.
"""

import logging
from typing import List, Optional
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.company import Company
from app.models.financial_statements import (
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
)
from app.services.data_collection_client import DataCollectionClient, DataCollectionError
from app.services.company_service import CompanyService
from app.services.financial_statements_service import FinancialStatementsService
from app.core.exceptions import DataIntegrationError

logger = logging.getLogger(__name__)


class DataIntegrationService:
    """
    Service for integrating data from Data Collection microservice.
    
    Handles fetching data from external service and storing in local database.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        data_client: Optional[DataCollectionClient] = None,
    ):
        """
        Initialize Data Integration Service.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            data_client: Optional data collection client (for testing)
        """
        self.db = db
        self.tenant_id = tenant_id
        self.data_client = data_client or DataCollectionClient()
        self.company_service = CompanyService(db, tenant_id)
        self.statements_service = FinancialStatementsService(db, tenant_id)

    async def sync_company_data(self, ticker: str) -> Company:
        """
        Sync company data from Data Collection service.
        
        Fetches company info and creates/updates local company record.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Company model instance
            
        Raises:
            DataIntegrationError: If sync fails
        """
        try:
            # Fetch company info from data collection service
            logger.info(f"Fetching company info for {ticker}")
            company_data = await self.data_client.fetch_company_info(ticker)
            
            # Check if company already exists
            existing_company = await self.company_service.get_by_ticker(ticker)
            
            if existing_company:
                # Update existing company
                logger.info(f"Updating existing company {ticker}")
                updated = await self.company_service.update(
                    company_id=existing_company.id,
                    name=company_data.get("name"),
                    sector=company_data.get("sector"),
                    industry=company_data.get("industry"),
                    market_cap=company_data.get("market_cap"),
                    country=company_data.get("country"),
                    currency=company_data.get("currency"),
                    exchange=company_data.get("exchange"),
                    employees=company_data.get("employees"),
                    fiscal_year_end=company_data.get("fiscal_year_end"),
                )
                return updated
            else:
                # Create new company
                logger.info(f"Creating new company {ticker}")
                created = await self.company_service.create(
                    ticker=ticker,
                    name=company_data.get("name"),
                    sector=company_data.get("sector"),
                    industry=company_data.get("industry"),
                    market_cap=company_data.get("market_cap"),
                    country=company_data.get("country"),
                    currency=company_data.get("currency"),
                    exchange=company_data.get("exchange"),
                    employees=company_data.get("employees"),
                    fiscal_year_end=company_data.get("fiscal_year_end"),
                )
                return created
                
        except DataCollectionError as e:
            logger.error(f"Failed to sync company data for {ticker}: {e}")
            raise DataIntegrationError(f"Company sync failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error syncing company {ticker}: {e}")
            raise DataIntegrationError(f"Unexpected error: {str(e)}")

    async def sync_income_statements(
        self,
        company_id: int,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[IncomeStatement]:
        """
        Sync income statements from Data Collection service.
        
        Args:
            company_id: Company database ID
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of created income statement records
            
        Raises:
            DataIntegrationError: If sync fails
        """
        try:
            logger.info(f"Syncing income statements for {ticker}")
            statements_data = await self.data_client.fetch_income_statement(
                ticker=ticker,
                period_type=period_type,
                start_date=start_date,
                end_date=end_date,
            )
            
            created_statements = []
            
            for stmt_data in statements_data:
                # Check if statement already exists for this period
                fiscal_year = stmt_data.get("fiscal_year")
                period = stmt_data.get("period_type", period_type)
                
                query = select(IncomeStatement).where(
                    IncomeStatement.company_id == company_id,
                    IncomeStatement.fiscal_year == fiscal_year,
                    IncomeStatement.period_type == period,
                    IncomeStatement.tenant_id == self.tenant_id,
                )
                result = await self.db.execute(query)
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Skipping existing income statement {ticker} {fiscal_year} {period}")
                    continue
                
                # Create new statement
                statement = await self.statements_service.create_income_statement(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    period_type=period,
                    revenue=stmt_data.get("revenue"),
                    cost_of_revenue=stmt_data.get("cost_of_revenue"),
                    gross_profit=stmt_data.get("gross_profit"),
                    operating_expenses=stmt_data.get("operating_expenses"),
                    operating_income=stmt_data.get("operating_income"),
                    interest_expense=stmt_data.get("interest_expense"),
                    income_before_tax=stmt_data.get("income_before_tax"),
                    income_tax_expense=stmt_data.get("income_tax_expense"),
                    net_income=stmt_data.get("net_income"),
                    eps_basic=stmt_data.get("eps_basic"),
                    eps_diluted=stmt_data.get("eps_diluted"),
                    shares_outstanding_basic=stmt_data.get("shares_outstanding_basic"),
                    shares_outstanding_diluted=stmt_data.get("shares_outstanding_diluted"),
                    ebitda=stmt_data.get("ebitda"),
                    research_and_development=stmt_data.get("research_and_development"),
                    selling_general_administrative=stmt_data.get("selling_general_administrative"),
                    depreciation_amortization=stmt_data.get("depreciation_amortization"),
                    other_income_expense=stmt_data.get("other_income_expense"),
                )
                
                created_statements.append(statement)
                logger.info(f"Created income statement {ticker} {fiscal_year} {period}")
            
            return created_statements
            
        except DataCollectionError as e:
            logger.error(f"Failed to sync income statements for {ticker}: {e}")
            raise DataIntegrationError(f"Income statement sync failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error syncing income statements {ticker}: {e}")
            raise DataIntegrationError(f"Unexpected error: {str(e)}")

    async def sync_balance_sheets(
        self,
        company_id: int,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[BalanceSheet]:
        """
        Sync balance sheets from Data Collection service.
        
        Args:
            company_id: Company database ID
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of created balance sheet records
            
        Raises:
            DataIntegrationError: If sync fails
        """
        try:
            logger.info(f"Syncing balance sheets for {ticker}")
            statements_data = await self.data_client.fetch_balance_sheet(
                ticker=ticker,
                period_type=period_type,
                start_date=start_date,
                end_date=end_date,
            )
            
            created_statements = []
            
            for stmt_data in statements_data:
                fiscal_year = stmt_data.get("fiscal_year")
                period = stmt_data.get("period_type", period_type)
                
                # Check if exists
                query = select(BalanceSheet).where(
                    BalanceSheet.company_id == company_id,
                    BalanceSheet.fiscal_year == fiscal_year,
                    BalanceSheet.period_type == period,
                    BalanceSheet.tenant_id == self.tenant_id,
                )
                result = await self.db.execute(query)
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Skipping existing balance sheet {ticker} {fiscal_year} {period}")
                    continue
                
                # Create new statement
                statement = await self.statements_service.create_balance_sheet(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    period_type=period,
                    total_assets=stmt_data.get("total_assets"),
                    current_assets=stmt_data.get("current_assets"),
                    cash_and_equivalents=stmt_data.get("cash_and_equivalents"),
                    short_term_investments=stmt_data.get("short_term_investments"),
                    accounts_receivable=stmt_data.get("accounts_receivable"),
                    inventory=stmt_data.get("inventory"),
                    other_current_assets=stmt_data.get("other_current_assets"),
                    non_current_assets=stmt_data.get("non_current_assets"),
                    property_plant_equipment=stmt_data.get("property_plant_equipment"),
                    intangible_assets=stmt_data.get("intangible_assets"),
                    goodwill=stmt_data.get("goodwill"),
                    long_term_investments=stmt_data.get("long_term_investments"),
                    other_non_current_assets=stmt_data.get("other_non_current_assets"),
                    total_liabilities=stmt_data.get("total_liabilities"),
                    current_liabilities=stmt_data.get("current_liabilities"),
                    accounts_payable=stmt_data.get("accounts_payable"),
                    short_term_debt=stmt_data.get("short_term_debt"),
                    current_portion_long_term_debt=stmt_data.get("current_portion_long_term_debt"),
                    other_current_liabilities=stmt_data.get("other_current_liabilities"),
                    non_current_liabilities=stmt_data.get("non_current_liabilities"),
                    long_term_debt=stmt_data.get("long_term_debt"),
                    deferred_tax_liabilities=stmt_data.get("deferred_tax_liabilities"),
                    other_non_current_liabilities=stmt_data.get("other_non_current_liabilities"),
                    total_equity=stmt_data.get("total_equity"),
                    common_stock=stmt_data.get("common_stock"),
                    retained_earnings=stmt_data.get("retained_earnings"),
                    treasury_stock=stmt_data.get("treasury_stock"),
                    accumulated_other_comprehensive_income=stmt_data.get("accumulated_other_comprehensive_income"),
                )
                
                created_statements.append(statement)
                logger.info(f"Created balance sheet {ticker} {fiscal_year} {period}")
            
            return created_statements
            
        except DataCollectionError as e:
            logger.error(f"Failed to sync balance sheets for {ticker}: {e}")
            raise DataIntegrationError(f"Balance sheet sync failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error syncing balance sheets {ticker}: {e}")
            raise DataIntegrationError(f"Unexpected error: {str(e)}")

    async def sync_cash_flow_statements(
        self,
        company_id: int,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[CashFlowStatement]:
        """
        Sync cash flow statements from Data Collection service.
        
        Args:
            company_id: Company database ID
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            List of created cash flow statement records
            
        Raises:
            DataIntegrationError: If sync fails
        """
        try:
            logger.info(f"Syncing cash flow statements for {ticker}")
            statements_data = await self.data_client.fetch_cash_flow_statement(
                ticker=ticker,
                period_type=period_type,
                start_date=start_date,
                end_date=end_date,
            )
            
            created_statements = []
            
            for stmt_data in statements_data:
                fiscal_year = stmt_data.get("fiscal_year")
                period = stmt_data.get("period_type", period_type)
                
                # Check if exists
                query = select(CashFlowStatement).where(
                    CashFlowStatement.company_id == company_id,
                    CashFlowStatement.fiscal_year == fiscal_year,
                    CashFlowStatement.period_type == period,
                    CashFlowStatement.tenant_id == self.tenant_id,
                )
                result = await self.db.execute(query)
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Skipping existing cash flow statement {ticker} {fiscal_year} {period}")
                    continue
                
                # Create new statement
                statement = await self.statements_service.create_cash_flow_statement(
                    company_id=company_id,
                    fiscal_year=fiscal_year,
                    period_type=period,
                    net_income=stmt_data.get("net_income"),
                    depreciation_amortization=stmt_data.get("depreciation_amortization"),
                    stock_based_compensation=stmt_data.get("stock_based_compensation"),
                    deferred_income_taxes=stmt_data.get("deferred_income_taxes"),
                    changes_in_working_capital=stmt_data.get("changes_in_working_capital"),
                    accounts_receivable_change=stmt_data.get("accounts_receivable_change"),
                    inventory_change=stmt_data.get("inventory_change"),
                    accounts_payable_change=stmt_data.get("accounts_payable_change"),
                    other_operating_activities=stmt_data.get("other_operating_activities"),
                    operating_cash_flow=stmt_data.get("operating_cash_flow"),
                    capital_expenditures=stmt_data.get("capital_expenditures"),
                    acquisitions=stmt_data.get("acquisitions"),
                    investment_purchases=stmt_data.get("investment_purchases"),
                    investment_sales=stmt_data.get("investment_sales"),
                    other_investing_activities=stmt_data.get("other_investing_activities"),
                    investing_cash_flow=stmt_data.get("investing_cash_flow"),
                    debt_issued=stmt_data.get("debt_issued"),
                    debt_repayment=stmt_data.get("debt_repayment"),
                    common_stock_issued=stmt_data.get("common_stock_issued"),
                    common_stock_repurchased=stmt_data.get("common_stock_repurchased"),
                    dividends_paid=stmt_data.get("dividends_paid"),
                    other_financing_activities=stmt_data.get("other_financing_activities"),
                    financing_cash_flow=stmt_data.get("financing_cash_flow"),
                    net_change_in_cash=stmt_data.get("net_change_in_cash"),
                    free_cash_flow=stmt_data.get("free_cash_flow"),
                )
                
                created_statements.append(statement)
                logger.info(f"Created cash flow statement {ticker} {fiscal_year} {period}")
            
            return created_statements
            
        except DataCollectionError as e:
            logger.error(f"Failed to sync cash flow statements for {ticker}: {e}")
            raise DataIntegrationError(f"Cash flow statement sync failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error syncing cash flow statements {ticker}: {e}")
            raise DataIntegrationError(f"Unexpected error: {str(e)}")

    async def sync_all_financial_data(
        self,
        ticker: str,
        period_type: str = "annual",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """
        Sync all financial data for a company.
        
        Fetches company info and all financial statements.
        
        Args:
            ticker: Stock ticker symbol
            period_type: "annual" or "quarterly"
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting full sync for {ticker}")
        
        # Sync company data first
        company = await self.sync_company_data(ticker)
        
        # Sync all financial statements
        income_statements = await self.sync_income_statements(
            company_id=company.id,
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        balance_sheets = await self.sync_balance_sheets(
            company_id=company.id,
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        cash_flow_statements = await self.sync_cash_flow_statements(
            company_id=company.id,
            ticker=ticker,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        logger.info(f"Completed full sync for {ticker}")
        
        return {
            "company": company,
            "income_statements": len(income_statements),
            "balance_sheets": len(balance_sheets),
            "cash_flow_statements": len(cash_flow_statements),
            "total_records": len(income_statements) + len(balance_sheets) + len(cash_flow_statements),
        }
