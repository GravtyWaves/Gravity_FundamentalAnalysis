"""
Risk Assessment Service.

Comprehensive risk analysis including:
- Altman Z-Score (bankruptcy prediction)
- Beta calculation (market risk)
- Volatility metrics (30d, 90d)
- Value at Risk (VaR)
- Component risk scores
- Scenario-based risk analysis (Optimistic, Neutral, Pessimistic)
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np

from app.models.company import Company
from app.models.financial_statements import BalanceSheet, IncomeStatement
from app.models.ratios import FinancialRatio
from app.models.valuation_risk import MarketData, RiskAssessment

logger = logging.getLogger(__name__)


class RiskAssessmentService:
    """Service for comprehensive risk assessment."""

    def __init__(self, db: AsyncSession, tenant_id: UUID | str):
        """
        Initialize risk assessment service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    async def calculate_altman_z_score(
        self,
        company_id: UUID,
        balance_sheet: BalanceSheet,
        income_statement: IncomeStatement,
        market_cap: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Calculate Altman Z-Score for bankruptcy prediction.

        Formula (for public companies):
        Z = 1.2×(Working Capital/Total Assets)
          + 1.4×(Retained Earnings/Total Assets)
          + 3.3×(EBIT/Total Assets)
          + 0.6×(Market Value Equity/Total Liabilities)
          + 1.0×(Sales/Total Assets)

        Interpretation:
        - Z > 2.99: Safe Zone (low bankruptcy risk)
        - 1.81 < Z < 2.99: Grey Zone (moderate risk)
        - Z < 1.81: Distress Zone (high bankruptcy risk)

        Args:
            company_id: Company UUID
            balance_sheet: Balance sheet data
            income_statement: Income statement data
            market_cap: Market capitalization (optional)

        Returns:
            Dictionary with z_score and interpretation
        """
        try:
            total_assets = Decimal(balance_sheet.total_assets or 0)
            total_liabilities = Decimal(balance_sheet.total_liabilities or 0)

            if total_assets == 0:
                return {
                    "z_score": Decimal("0"),
                    "interpretation": "insufficient_data",
                    "risk_level": "unknown"
                }

            # Working Capital = Current Assets - Current Liabilities
            working_capital = Decimal(
                (balance_sheet.current_assets or 0) -
                (balance_sheet.current_liabilities or 0)
            )

            # Retained Earnings
            retained_earnings = Decimal(balance_sheet.retained_earnings or 0)

            # EBIT = Operating Income
            ebit = Decimal(income_statement.operating_income or 0)

            # Sales = Revenue
            sales = Decimal(income_statement.revenue or 0)

            # Market Value of Equity (use market cap if available, else book value)
            if market_cap:
                market_value_equity = market_cap
            else:
                market_value_equity = Decimal(balance_sheet.total_equity or 0)

            # Calculate Z-Score components
            x1 = working_capital / total_assets if total_assets > 0 else Decimal("0")
            x2 = retained_earnings / total_assets if total_assets > 0 else Decimal("0")
            x3 = ebit / total_assets if total_assets > 0 else Decimal("0")
            x4 = (market_value_equity / total_liabilities
                  if total_liabilities > 0 else Decimal("0"))
            x5 = sales / total_assets if total_assets > 0 else Decimal("0")

            # Z-Score calculation
            z_score = (
                Decimal("1.2") * x1 +
                Decimal("1.4") * x2 +
                Decimal("3.3") * x3 +
                Decimal("0.6") * x4 +
                Decimal("1.0") * x5
            )

            # Interpretation
            if z_score > Decimal("2.99"):
                interpretation = "safe_zone"
                risk_level = "low"
            elif z_score > Decimal("1.81"):
                interpretation = "grey_zone"
                risk_level = "moderate"
            else:
                interpretation = "distress_zone"
                risk_level = "high"

            return {
                "z_score": z_score,
                "interpretation": interpretation,
                "risk_level": risk_level,
                "components": {
                    "working_capital_ratio": x1,
                    "retained_earnings_ratio": x2,
                    "ebit_ratio": x3,
                    "market_value_ratio": x4,
                    "sales_turnover": x5,
                }
            }

        except Exception as e:
            logger.error(f"Error calculating Altman Z-Score: {e}")
            return {
                "z_score": Decimal("0"),
                "interpretation": "calculation_error",
                "risk_level": "unknown"
            }

    async def calculate_beta(
        self,
        company_id: UUID,
        period_days: int = 252,  # 1 year of trading days
    ) -> Optional[Decimal]:
        """
        Calculate Beta (market risk measure).

        Beta = Covariance(Stock Returns, Market Returns) / Variance(Market Returns)

        Args:
            company_id: Company UUID
            period_days: Number of trading days for calculation

        Returns:
            Beta value or None if insufficient data
        """
        try:
            # Get historical market data for the company
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days * 2)  # Buffer for weekends

            query = select(MarketData).where(
                and_(
                    MarketData.company_id == company_id,
                    MarketData.date >= start_date,
                    MarketData.date <= end_date,
                    MarketData.tenant_id == self.tenant_id,
                )
            ).order_by(MarketData.date)

            result = await self.db.execute(query)
            market_data_list = result.scalars().all()

            if len(market_data_list) < 30:  # Minimum data requirement
                logger.warning(f"Insufficient data for beta calculation: {len(market_data_list)} days")
                return None

            # Calculate daily returns
            prices = [float(md.close_price) for md in market_data_list]
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(daily_return)

            if len(returns) < 30:
                return None

            # For now, assume market returns (would need market index data)
            # Placeholder: use average return as proxy
            # In production, fetch actual market index (S&P 500, etc.)
            market_returns = returns  # Simplified

            # Calculate covariance and variance
            stock_returns_array = np.array(returns)
            market_returns_array = np.array(market_returns)

            covariance = np.cov(stock_returns_array, market_returns_array)[0][1]
            market_variance = np.var(market_returns_array)

            if market_variance == 0:
                return Decimal("1.0")

            beta = covariance / market_variance

            return Decimal(str(round(beta, 4)))

        except Exception as e:
            logger.error(f"Error calculating beta: {e}")
            return None

    async def calculate_volatility(
        self,
        company_id: UUID,
        period_days: int = 30,
    ) -> Optional[Decimal]:
        """
        Calculate historical volatility (standard deviation of returns).

        Args:
            company_id: Company UUID
            period_days: Number of days for calculation

        Returns:
            Annualized volatility or None
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days * 2)

            query = select(MarketData).where(
                and_(
                    MarketData.company_id == company_id,
                    MarketData.date >= start_date,
                    MarketData.date <= end_date,
                    MarketData.tenant_id == self.tenant_id,
                )
            ).order_by(MarketData.date)

            result = await self.db.execute(query)
            market_data_list = result.scalars().all()

            if len(market_data_list) < 10:
                return None

            # Calculate daily returns
            prices = [float(md.close_price) for md in market_data_list]
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(daily_return)

            if len(returns) < 5:
                return None

            # Calculate standard deviation
            std_dev = np.std(returns)

            # Annualize (assuming 252 trading days per year)
            annualized_volatility = std_dev * np.sqrt(252)

            return Decimal(str(round(annualized_volatility, 4)))

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None

    async def calculate_value_at_risk(
        self,
        company_id: UUID,
        confidence_level: float = 0.95,
        period_days: int = 30,
    ) -> Optional[Decimal]:
        """
        Calculate Value at Risk (VaR) at specified confidence level.

        VaR_95% = μ - 1.65σ (for 95% confidence)

        Args:
            company_id: Company UUID
            confidence_level: Confidence level (0.95 for 95%)
            period_days: Historical period for calculation

        Returns:
            VaR as percentage or None
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days * 2)

            query = select(MarketData).where(
                and_(
                    MarketData.company_id == company_id,
                    MarketData.date >= start_date,
                    MarketData.date <= end_date,
                    MarketData.tenant_id == self.tenant_id,
                )
            ).order_by(MarketData.date)

            result = await self.db.execute(query)
            market_data_list = result.scalars().all()

            if len(market_data_list) < 10:
                return None

            # Calculate daily returns
            prices = [float(md.close_price) for md in market_data_list]
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(daily_return)

            if len(returns) < 5:
                return None

            # Calculate mean and std dev
            mean_return = np.mean(returns)
            std_dev = np.std(returns)

            # Z-score for confidence level
            if confidence_level == 0.95:
                z_score = 1.65
            elif confidence_level == 0.99:
                z_score = 2.33
            else:
                z_score = 1.65

            # VaR calculation
            var = mean_return - z_score * std_dev

            return Decimal(str(round(var, 6)))

        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return None

    def calculate_component_risks(
        self,
        financial_ratios: FinancialRatio,
        altman_z_score: Decimal,
    ) -> Dict[str, Decimal]:
        """
        Calculate component risk scores (0-100, higher = more risky).

        Args:
            financial_ratios: Financial ratios object
            altman_z_score: Altman Z-Score

        Returns:
            Dictionary of risk component scores
        """
        # Financial Risk (based on leverage)
        debt_to_equity = financial_ratios.debt_to_equity or Decimal("0")
        interest_coverage = financial_ratios.interest_coverage or Decimal("999")
        
        if debt_to_equity > Decimal("2.0"):  # type: ignore[operator]
            financial_risk = Decimal("80")
        elif debt_to_equity > Decimal("1.0"):  # type: ignore[operator]
            financial_risk = Decimal("50")
        elif debt_to_equity > Decimal("0.5"):  # type: ignore[operator]
            financial_risk = Decimal("30")
        else:
            financial_risk = Decimal("10")

        if interest_coverage < Decimal("1.5"):  # type: ignore[operator]
            financial_risk = min(financial_risk + Decimal("20"), Decimal("100"))

        # Operational Risk (based on profitability)
        operating_margin = financial_ratios.operating_margin or Decimal("0")
        roe = financial_ratios.roe or Decimal("0")

        if operating_margin < Decimal("0"):  # type: ignore[operator]
            operational_risk = Decimal("80")
        elif operating_margin < Decimal("0.05"):  # type: ignore[operator]
            operational_risk = Decimal("60")
        elif operating_margin < Decimal("0.15"):  # type: ignore[operator]
            operational_risk = Decimal("30")
        else:
            operational_risk = Decimal("10")

        # Business Risk (based on Z-Score and growth)
        if altman_z_score < Decimal("1.81"):
            business_risk = Decimal("80")
        elif altman_z_score < Decimal("2.99"):
            business_risk = Decimal("40")
        else:
            business_risk = Decimal("15")

        # Market Risk (placeholder - would use beta/volatility)
        market_risk = Decimal("30")  # Medium default

        # ESG Risk (placeholder - would require ESG data)
        esg_risk = Decimal("50")  # Neutral default

        return {
            "financial_risk_score": financial_risk,
            "operational_risk_score": operational_risk,
            "business_risk_score": business_risk,
            "market_risk_score": market_risk,
            "esg_risk_score": esg_risk,
        }

    def calculate_overall_risk_score(
        self,
        component_scores: Dict[str, Decimal],
    ) -> Decimal:
        """
        Calculate weighted overall risk score.

        Args:
            component_scores: Dictionary of component risk scores

        Returns:
            Overall risk score (0-100)
        """
        weights = {
            "financial_risk_score": Decimal("0.30"),
            "operational_risk_score": Decimal("0.25"),
            "business_risk_score": Decimal("0.25"),
            "market_risk_score": Decimal("0.15"),
            "esg_risk_score": Decimal("0.05"),
        }

        overall_score = sum(
            component_scores.get(key, Decimal("50")) * weight
            for key, weight in weights.items()
        )

        return Decimal(str(round(overall_score, 2)))

    def get_risk_rating(self, overall_score: Decimal) -> str:
        """
        Convert overall risk score to rating.

        Args:
            overall_score: Overall risk score (0-100)

        Returns:
            Risk rating string
        """
        if overall_score < Decimal("25"):
            return "Low"
        elif overall_score < Decimal("50"):
            return "Medium"
        elif overall_score < Decimal("75"):
            return "High"
        else:
            return "Very High"

    async def assess_risk_with_scenarios(
        self,
        company_id: UUID,
        assessment_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive risk assessment with three scenarios.

        Scenarios:
        - Optimistic: Best case assumptions
        - Neutral: Base case (current data)
        - Pessimistic: Worst case assumptions

        Args:
            company_id: Company UUID
            assessment_date: Date of assessment (default: today)

        Returns:
            Dictionary with risk assessment for all three scenarios
        """
        if assessment_date is None:
            assessment_date = date.today()

        try:
            # Fetch latest financial data
            latest_bs_query = select(BalanceSheet).where(
                and_(
                    BalanceSheet.company_id == company_id,
                    BalanceSheet.tenant_id == self.tenant_id,
                )
            ).order_by(BalanceSheet.fiscal_year.desc()).limit(1)

            latest_is_query = select(IncomeStatement).where(
                and_(
                    IncomeStatement.company_id == company_id,
                    IncomeStatement.tenant_id == self.tenant_id,
                )
            ).order_by(IncomeStatement.fiscal_year.desc()).limit(1)

            latest_ratios_query = select(FinancialRatio).where(
                and_(
                    FinancialRatio.company_id == company_id,
                    FinancialRatio.tenant_id == self.tenant_id,
                )
            ).order_by(FinancialRatio.calculation_date.desc()).limit(1)

            bs_result = await self.db.execute(latest_bs_query)
            is_result = await self.db.execute(latest_is_query)
            ratios_result = await self.db.execute(latest_ratios_query)

            balance_sheet = bs_result.scalar_one_or_none()
            income_statement = is_result.scalar_one_or_none()
            financial_ratios = ratios_result.scalar_one_or_none()

            if not all([balance_sheet, income_statement, financial_ratios]):
                raise ValueError("Insufficient financial data for risk assessment")

            # Get market data
            latest_market_query = select(MarketData).where(
                and_(
                    MarketData.company_id == company_id,
                    MarketData.tenant_id == self.tenant_id,
                )
            ).order_by(MarketData.date.desc()).limit(1)

            market_result = await self.db.execute(latest_market_query)
            market_data = market_result.scalar_one_or_none()

            market_cap = market_data.market_cap if market_data else None

            # Ensure we have required data
            if balance_sheet is None or income_statement is None:
                raise ValueError("Missing required financial statements")
            if financial_ratios is None:
                raise ValueError("Missing required financial ratios")

            # === NEUTRAL SCENARIO (Base Case) ===
            z_score_neutral = await self.calculate_altman_z_score(
                company_id, balance_sheet, income_statement, market_cap
            )

            beta_neutral = await self.calculate_beta(company_id, period_days=252)
            volatility_30d_neutral = await self.calculate_volatility(company_id, 30)
            volatility_90d_neutral = await self.calculate_volatility(company_id, 90)
            var_95_neutral = await self.calculate_value_at_risk(company_id, 0.95, 30)

            component_risks_neutral = self.calculate_component_risks(
                financial_ratios, z_score_neutral["z_score"]
            )
            overall_score_neutral = self.calculate_overall_risk_score(component_risks_neutral)
            risk_rating_neutral = self.get_risk_rating(overall_score_neutral)

            # === OPTIMISTIC SCENARIO ===
            # Assume 20% improvement in key metrics
            optimistic_factor = Decimal("0.80")  # 20% less risk
            component_risks_optimistic = {
                k: v * optimistic_factor for k, v in component_risks_neutral.items()
            }
            overall_score_optimistic = self.calculate_overall_risk_score(component_risks_optimistic)
            risk_rating_optimistic = self.get_risk_rating(overall_score_optimistic)

            # === PESSIMISTIC SCENARIO ===
            # Assume 30% deterioration in key metrics
            pessimistic_factor = Decimal("1.30")  # 30% more risk
            component_risks_pessimistic = {
                k: min(v * pessimistic_factor, Decimal("100")) 
                for k, v in component_risks_neutral.items()
            }
            overall_score_pessimistic = self.calculate_overall_risk_score(component_risks_pessimistic)
            risk_rating_pessimistic = self.get_risk_rating(overall_score_pessimistic)

            # Create risk assessment records
            scenarios = {}

            for scenario_name, overall_score, risk_rating, component_risks in [
                ("neutral", overall_score_neutral, risk_rating_neutral, component_risks_neutral),
                ("optimistic", overall_score_optimistic, risk_rating_optimistic, component_risks_optimistic),
                ("pessimistic", overall_score_pessimistic, risk_rating_pessimistic, component_risks_pessimistic),
            ]:
                risk_assessment = RiskAssessment(
                    company_id=company_id,
                    tenant_id=self.tenant_id,
                    assessment_date=assessment_date,
                    overall_risk_score=overall_score,
                    risk_rating=risk_rating,
                    business_risk_score=component_risks.get("business_risk_score"),
                    financial_risk_score=component_risks.get("financial_risk_score"),
                    operational_risk_score=component_risks.get("operational_risk_score"),
                    market_risk_score=component_risks.get("market_risk_score"),
                    esg_risk_score=component_risks.get("esg_risk_score"),
                    altman_z_score=z_score_neutral["z_score"],
                    beta=beta_neutral,
                    volatility_30d=volatility_30d_neutral,
                    volatility_90d=volatility_90d_neutral,
                    value_at_risk_95=var_95_neutral,
                    risk_factors={
                        "scenario": scenario_name,
                        "z_score_interpretation": z_score_neutral["interpretation"],
                        "z_score_risk_level": z_score_neutral["risk_level"],
                    },
                    risk_details={
                        "scenario_assumptions": {
                            "optimistic": "20% improvement in risk metrics",
                            "neutral": "Current market conditions",
                            "pessimistic": "30% deterioration in risk metrics",
                        }[scenario_name]
                    }
                )

                self.db.add(risk_assessment)
                scenarios[scenario_name] = risk_assessment

            await self.db.commit()

            return {
                "company_id": str(company_id),
                "assessment_date": assessment_date.isoformat() if assessment_date else date.today().isoformat(),
                "scenarios": {
                    "optimistic": {
                        "overall_risk_score": float(overall_score_optimistic),
                        "risk_rating": risk_rating_optimistic,
                        "component_risks": {k: float(v) for k, v in component_risks_optimistic.items()},
                    },
                    "neutral": {
                        "overall_risk_score": float(overall_score_neutral),
                        "risk_rating": risk_rating_neutral,
                        "component_risks": {k: float(v) for k, v in component_risks_neutral.items()},
                        "altman_z_score": float(z_score_neutral["z_score"]),
                        "z_score_interpretation": z_score_neutral["interpretation"],
                        "beta": float(beta_neutral) if beta_neutral else None,
                        "volatility_30d": float(volatility_30d_neutral) if volatility_30d_neutral else None,
                        "volatility_90d": float(volatility_90d_neutral) if volatility_90d_neutral else None,
                        "var_95": float(var_95_neutral) if var_95_neutral else None,
                    },
                    "pessimistic": {
                        "overall_risk_score": float(overall_score_pessimistic),
                        "risk_rating": risk_rating_pessimistic,
                        "component_risks": {k: float(v) for k, v in component_risks_pessimistic.items()},
                    },
                },
            }

        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            await self.db.rollback()
            raise

    async def get_latest_risk_assessment(
        self,
        company_id: UUID,
    ) -> Optional[RiskAssessment]:
        """
        Get latest risk assessment for a company.

        Args:
            company_id: Company UUID

        Returns:
            Latest RiskAssessment or None
        """
        query = select(RiskAssessment).where(
            and_(
                RiskAssessment.company_id == company_id,
                RiskAssessment.tenant_id == self.tenant_id,
            )
        ).order_by(RiskAssessment.assessment_date.desc()).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
