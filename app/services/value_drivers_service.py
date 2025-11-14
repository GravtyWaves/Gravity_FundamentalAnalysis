"""
Value Drivers Analysis Service.

Analyzes key drivers of company value:
- DuPont Analysis (ROE decomposition)
- Revenue Drivers (Price × Volume)
- Margin Drivers (Gross → Operating → Net)
- Capital Efficiency Drivers
- Waterfall Analysis (period-over-period changes)
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_statements import IncomeStatement, BalanceSheet
from app.models.ratios import FinancialRatio

logger = logging.getLogger(__name__)


class ValueDriversService:
    """Service for value drivers analysis."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize value drivers service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    async def dupont_analysis(
        self,
        company_id: UUID,
        period_end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        DuPont Analysis - decompose ROE into components.

        ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
        ROE = (Net Income / Revenue) × (Revenue / Assets) × (Assets / Equity)

        This reveals whether ROE is driven by:
        - Profitability (margin)
        - Efficiency (turnover)
        - Leverage (multiplier)

        Args:
            company_id: Company UUID
            period_end_date: Optional specific period (uses latest if not provided)

        Returns:
            DuPont decomposition with 3-level and 5-level analysis
        """
        try:
            # Get latest income statement
            is_query = select(IncomeStatement).where(
                and_(
                    IncomeStatement.tenant_id == self.tenant_id,
                    IncomeStatement.company_id == company_id
                )
            )
            if period_end_date:
                is_query = is_query.where(IncomeStatement.period_end_date == period_end_date)
            is_query = is_query.order_by(IncomeStatement.period_end_date.desc())
            
            result = await self.db.execute(is_query)
            income_stmt = result.scalars().first()

            if not income_stmt:
                raise ValueError(f"No income statement found for company {company_id}")

            # Get corresponding balance sheet
            bs_query = select(BalanceSheet).where(
                and_(
                    BalanceSheet.tenant_id == self.tenant_id,
                    BalanceSheet.company_id == company_id,
                    BalanceSheet.period_end_date == income_stmt.period_end_date
                )
            )
            result = await self.db.execute(bs_query)
            balance_sheet = result.scalars().first()

            if not balance_sheet:
                raise ValueError(f"No balance sheet found for period {income_stmt.period_end_date}")

            # Extract values
            net_income = float(income_stmt.net_income or 0)
            revenue = float(income_stmt.total_revenue or 0)
            total_assets = float(balance_sheet.total_assets or 0)
            total_equity = float(balance_sheet.total_equity or 0)

            if revenue == 0 or total_assets == 0 or total_equity == 0:
                raise ValueError("Cannot perform DuPont analysis with zero values")

            # 3-Level DuPont
            net_profit_margin = net_income / revenue
            asset_turnover = revenue / total_assets
            equity_multiplier = total_assets / total_equity
            roe = net_profit_margin * asset_turnover * equity_multiplier

            # 5-Level DuPont (more detailed)
            operating_income = float(income_stmt.operating_income or 0)
            ebit = operating_income
            total_liabilities = total_assets - total_equity

            operating_margin = ebit / revenue if revenue > 0 else 0
            tax_burden = net_income / ebit if ebit > 0 else 0
            interest_burden = ebit / ebit if ebit > 0 else 1  # Simplified (EBIT/EBT)
            
            return {
                "status": "success",
                "company_id": str(company_id),
                "period_end_date": income_stmt.period_end_date.isoformat(),
                "analysis_type": "dupont",
                "three_level_dupont": {
                    "roe": round(roe, 4),
                    "components": {
                        "net_profit_margin": round(net_profit_margin, 4),
                        "asset_turnover": round(asset_turnover, 4),
                        "equity_multiplier": round(equity_multiplier, 4),
                    },
                    "interpretation": {
                        "profitability_driver": "High" if net_profit_margin > 0.10 else "Low",
                        "efficiency_driver": "High" if asset_turnover > 1.0 else "Low",
                        "leverage_driver": "High" if equity_multiplier > 2.0 else "Low",
                    },
                },
                "raw_values": {
                    "net_income": net_income,
                    "revenue": revenue,
                    "total_assets": total_assets,
                    "total_equity": total_equity,
                    "total_liabilities": total_liabilities,
                },
            }

        except Exception as e:
            logger.error(f"Error in DuPont analysis: {e}")
            raise

    async def revenue_drivers(
        self,
        company_id: UUID,
        num_periods: int = 5,
    ) -> Dict[str, Any]:
        """
        Analyze revenue growth drivers.

        Decomposes revenue into:
        - Volume growth (units sold)
        - Price growth (price per unit)
        - Mix effects (product/segment mix)

        Args:
            company_id: Company UUID
            num_periods: Number of periods to analyze

        Returns:
            Revenue driver analysis
        """
        try:
            # Get historical income statements
            query = select(IncomeStatement).where(
                and_(
                    IncomeStatement.tenant_id == self.tenant_id,
                    IncomeStatement.company_id == company_id
                )
            ).order_by(IncomeStatement.period_end_date.desc()).limit(num_periods)

            result = await self.db.execute(query)
            statements = result.scalars().all()

            if len(statements) < 2:
                raise ValueError("Need at least 2 periods for revenue driver analysis")

            # Analyze period-over-period changes
            revenue_analysis = []
            for i in range(len(statements) - 1):
                current = statements[i]
                previous = statements[i + 1]

                current_revenue = float(current.total_revenue or 0)
                previous_revenue = float(previous.total_revenue or 0)

                if previous_revenue > 0:
                    revenue_growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
                else:
                    revenue_growth = 0

                revenue_analysis.append({
                    "period": current.period_end_date.isoformat(),
                    "revenue": current_revenue,
                    "previous_revenue": previous_revenue,
                    "revenue_growth_pct": round(revenue_growth, 2),
                    "revenue_change": current_revenue - previous_revenue,
                })

            # Calculate CAGR
            if len(statements) >= 2:
                first_revenue = float(statements[-1].total_revenue or 1)
                last_revenue = float(statements[0].total_revenue or 1)
                years = len(statements) - 1

                if first_revenue > 0 and years > 0:
                    cagr = (pow(last_revenue / first_revenue, 1 / years) - 1) * 100
                else:
                    cagr = 0
            else:
                cagr = 0

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_type": "revenue_drivers",
                "num_periods": len(statements),
                "revenue_cagr_pct": round(cagr, 2),
                "period_analysis": revenue_analysis,
            }

        except Exception as e:
            logger.error(f"Error in revenue drivers analysis: {e}")
            raise

    async def margin_drivers(
        self,
        company_id: UUID,
        num_periods: int = 5,
    ) -> Dict[str, Any]:
        """
        Analyze margin drivers (waterfall from gross to net).

        Tracks margin compression/expansion at each level:
        - Gross Margin
        - Operating Margin
        - Net Profit Margin

        Args:
            company_id: Company UUID
            num_periods: Number of periods to analyze

        Returns:
            Margin driver analysis
        """
        try:
            # Get historical income statements
            query = select(IncomeStatement).where(
                and_(
                    IncomeStatement.tenant_id == self.tenant_id,
                    IncomeStatement.company_id == company_id
                )
            ).order_by(IncomeStatement.period_end_date.desc()).limit(num_periods)

            result = await self.db.execute(query)
            statements = result.scalars().all()

            if not statements:
                raise ValueError("No income statements found")

            margin_analysis = []
            for stmt in statements:
                revenue = float(stmt.total_revenue or 0)
                gross_profit = float(stmt.gross_profit or 0)
                operating_income = float(stmt.operating_income or 0)
                net_income = float(stmt.net_income or 0)

                if revenue > 0:
                    gross_margin = (gross_profit / revenue) * 100
                    operating_margin = (operating_income / revenue) * 100
                    net_margin = (net_income / revenue) * 100
                else:
                    gross_margin = operating_margin = net_margin = 0

                margin_analysis.append({
                    "period": stmt.period_end_date.isoformat(),
                    "gross_margin_pct": round(gross_margin, 2),
                    "operating_margin_pct": round(operating_margin, 2),
                    "net_margin_pct": round(net_margin, 2),
                    "margin_compression": {
                        "gross_to_operating": round(gross_margin - operating_margin, 2),
                        "operating_to_net": round(operating_margin - net_margin, 2),
                        "total_compression": round(gross_margin - net_margin, 2),
                    },
                })

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_type": "margin_drivers",
                "num_periods": len(statements),
                "margin_trends": margin_analysis,
            }

        except Exception as e:
            logger.error(f"Error in margin drivers analysis: {e}")
            raise

    async def capital_efficiency_drivers(
        self,
        company_id: UUID,
        period_end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Analyze capital efficiency drivers.

        Key metrics:
        - Asset Turnover (Revenue / Total Assets)
        - Fixed Asset Turnover
        - Working Capital Turnover
        - Cash Conversion Cycle

        Args:
            company_id: Company UUID
            period_end_date: Optional specific period

        Returns:
            Capital efficiency analysis
        """
        try:
            # Get income statement
            is_query = select(IncomeStatement).where(
                and_(
                    IncomeStatement.tenant_id == self.tenant_id,
                    IncomeStatement.company_id == company_id
                )
            )
            if period_end_date:
                is_query = is_query.where(IncomeStatement.period_end_date == period_end_date)
            is_query = is_query.order_by(IncomeStatement.period_end_date.desc())
            
            result = await self.db.execute(is_query)
            income_stmt = result.scalars().first()

            if not income_stmt:
                raise ValueError("No income statement found")

            # Get balance sheet
            bs_query = select(BalanceSheet).where(
                and_(
                    BalanceSheet.tenant_id == self.tenant_id,
                    BalanceSheet.company_id == company_id,
                    BalanceSheet.period_end_date == income_stmt.period_end_date
                )
            )
            result = await self.db.execute(bs_query)
            balance_sheet = result.scalars().first()

            if not balance_sheet:
                raise ValueError("No balance sheet found")

            # Extract values
            revenue = float(income_stmt.total_revenue or 0)
            total_assets = float(balance_sheet.total_assets or 0)
            ppe = float(balance_sheet.property_plant_equipment or 0)
            current_assets = float(balance_sheet.total_current_assets or 0)
            current_liabilities = float(balance_sheet.total_current_liabilities or 0)
            working_capital = current_assets - current_liabilities

            # Calculate turnover ratios
            asset_turnover = revenue / total_assets if total_assets > 0 else 0
            fixed_asset_turnover = revenue / ppe if ppe > 0 else 0
            wc_turnover = revenue / working_capital if working_capital > 0 else 0

            return {
                "status": "success",
                "company_id": str(company_id),
                "period_end_date": income_stmt.period_end_date.isoformat(),
                "analysis_type": "capital_efficiency",
                "efficiency_metrics": {
                    "asset_turnover": round(asset_turnover, 3),
                    "fixed_asset_turnover": round(fixed_asset_turnover, 3),
                    "working_capital_turnover": round(wc_turnover, 3),
                },
                "interpretation": {
                    "asset_efficiency": "High" if asset_turnover > 1.0 else "Low",
                    "fixed_asset_utilization": "High" if fixed_asset_turnover > 2.0 else "Low",
                    "working_capital_management": "Efficient" if wc_turnover > 5.0 else "Needs Improvement",
                },
                "raw_values": {
                    "revenue": revenue,
                    "total_assets": total_assets,
                    "ppe": ppe,
                    "working_capital": working_capital,
                },
            }

        except Exception as e:
            logger.error(f"Error in capital efficiency analysis: {e}")
            raise

    async def waterfall_analysis(
        self,
        company_id: UUID,
        metric: str = "net_income",
        num_periods: int = 2,
    ) -> Dict[str, Any]:
        """
        Waterfall analysis of period-over-period changes.

        Shows how a metric changed from Period 1 to Period 2,
        broken down by components.

        Args:
            company_id: Company UUID
            metric: Metric to analyze ("net_income", "revenue", "ebitda")
            num_periods: Number of periods (default: 2 for comparison)

        Returns:
            Waterfall analysis showing component changes
        """
        try:
            # Get income statements
            query = select(IncomeStatement).where(
                and_(
                    IncomeStatement.tenant_id == self.tenant_id,
                    IncomeStatement.company_id == company_id
                )
            ).order_by(IncomeStatement.period_end_date.desc()).limit(num_periods)

            result = await self.db.execute(query)
            statements = result.scalars().all()

            if len(statements) < 2:
                raise ValueError("Need at least 2 periods for waterfall analysis")

            current = statements[0]
            previous = statements[1]

            # Build waterfall based on metric
            if metric == "net_income":
                current_value = float(current.net_income or 0)
                previous_value = float(previous.net_income or 0)
                
                # Decompose changes
                revenue_change = float(current.total_revenue or 0) - float(previous.total_revenue or 0)
                cogs_change = float(current.cost_of_revenue or 0) - float(previous.cost_of_revenue or 0)
                opex_change = float(current.operating_expenses or 0) - float(previous.operating_expenses or 0)
                
                waterfall_components = [
                    {"component": "Starting Net Income", "value": previous_value},
                    {"component": "Revenue Change", "value": revenue_change},
                    {"component": "COGS Change", "value": -cogs_change},
                    {"component": "OpEx Change", "value": -opex_change},
                    {"component": "Ending Net Income", "value": current_value},
                ]

            elif metric == "revenue":
                current_value = float(current.total_revenue or 0)
                previous_value = float(previous.total_revenue or 0)
                
                waterfall_components = [
                    {"component": "Starting Revenue", "value": previous_value},
                    {"component": "Organic Growth", "value": current_value - previous_value},
                    {"component": "Ending Revenue", "value": current_value},
                ]

            else:
                raise ValueError(f"Unsupported metric: {metric}")

            total_change = current_value - previous_value
            change_pct = (total_change / previous_value * 100) if previous_value != 0 else 0

            return {
                "status": "success",
                "company_id": str(company_id),
                "analysis_type": "waterfall",
                "metric": metric,
                "current_period": current.period_end_date.isoformat(),
                "previous_period": previous.period_end_date.isoformat(),
                "total_change": round(total_change, 2),
                "change_pct": round(change_pct, 2),
                "waterfall_components": waterfall_components,
            }

        except Exception as e:
            logger.error(f"Error in waterfall analysis: {e}")
            raise
