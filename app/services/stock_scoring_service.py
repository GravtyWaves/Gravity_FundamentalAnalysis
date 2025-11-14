"""
Stock Scoring and Ranking Service.

Comprehensive fundamental scoring system for stock evaluation and ranking.
Scores are calculated across multiple dimensions:
- Valuation (P/E, P/B, DCF)
- Profitability (ROE, ROA, Margins)
- Growth (Revenue, Earnings, CAGR)
- Financial Health (Debt, Liquidity)
- Risk (Volatility, Beta, Z-Score)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.ratios import FinancialRatio
from app.models.valuation_risk import Valuation
from app.services.ratio_calculation_service import RatioCalculationService
from app.services.risk_assessment_service import RiskAssessmentService

logger = logging.getLogger(__name__)


class StockScoringService:
    """Service for stock scoring and ranking."""

    # Scoring weights (total = 100%)
    WEIGHTS = {
        "valuation": 0.25,      # 25%
        "profitability": 0.20,  # 20%
        "growth": 0.20,         # 20%
        "financial_health": 0.20,  # 20%
        "risk": 0.15,           # 15%
    }

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize stock scoring service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id
        self.ratio_service = RatioCalculationService(db, tenant_id)
        self.risk_service = RiskAssessmentService(db, tenant_id)

    async def calculate_valuation_score(
        self,
        company_id: UUID,
        ratios: Dict[str, Decimal],
    ) -> Tuple[float, Dict[str, any]]:
        """
        Calculate valuation score (0-100).

        Considers:
        - P/E ratio (lower is better)
        - P/B ratio (lower is better)
        - PEG ratio (lower is better)
        - EV/EBITDA (lower is better)

        Args:
            company_id: Company UUID
            ratios: Dictionary of ratio values

        Returns:
            Tuple of (score, breakdown)
        """
        scores = []
        breakdown = {}

        # P/E ratio scoring (inverse scoring, lower P/E = higher score)
        pe_ratio = ratios.get("price_to_earnings_ratio")
        if pe_ratio and pe_ratio > 0:
            # Benchmark: P/E < 15 = 100, P/E = 25 = 50, P/E > 40 = 0
            pe_score = max(0, min(100, 100 - (float(pe_ratio) - 15) * 3.33))
            scores.append(pe_score)
            breakdown["pe_score"] = round(pe_score, 2)
        
        # P/B ratio scoring (lower P/B = higher score)
        pb_ratio = ratios.get("price_to_book_ratio")
        if pb_ratio and pb_ratio > 0:
            # Benchmark: P/B < 1 = 100, P/B = 3 = 50, P/B > 5 = 0
            pb_score = max(0, min(100, 100 - (float(pb_ratio) - 1) * 25))
            scores.append(pb_score)
            breakdown["pb_score"] = round(pb_score, 2)

        # PEG ratio scoring (lower PEG = higher score)
        peg_ratio = ratios.get("peg_ratio")
        if peg_ratio and peg_ratio > 0:
            # Benchmark: PEG < 1 = 100, PEG = 2 = 50, PEG > 3 = 0
            peg_score = max(0, min(100, 100 - (float(peg_ratio) - 1) * 50))
            scores.append(peg_score)
            breakdown["peg_score"] = round(peg_score, 2)

        # EV/EBITDA ratio scoring
        ev_ebitda = ratios.get("ev_to_ebitda_ratio")
        if ev_ebitda and ev_ebitda > 0:
            # Benchmark: EV/EBITDA < 8 = 100, EV/EBITDA = 12 = 50, EV/EBITDA > 18 = 0
            ev_score = max(0, min(100, 100 - (float(ev_ebitda) - 8) * 5))
            scores.append(ev_score)
            breakdown["ev_ebitda_score"] = round(ev_score, 2)

        final_score = sum(scores) / len(scores) if scores else 0
        return final_score, breakdown

    async def calculate_profitability_score(
        self,
        company_id: UUID,
        ratios: Dict[str, Decimal],
    ) -> Tuple[float, Dict[str, any]]:
        """
        Calculate profitability score (0-100).

        Considers:
        - ROE (higher is better)
        - ROA (higher is better)
        - Net Profit Margin (higher is better)
        - Operating Margin (higher is better)

        Args:
            company_id: Company UUID
            ratios: Dictionary of ratio values

        Returns:
            Tuple of (score, breakdown)
        """
        scores = []
        breakdown = {}

        # ROE scoring
        roe = ratios.get("return_on_equity")
        if roe:
            # Benchmark: ROE > 20% = 100, ROE = 10% = 50, ROE < 5% = 0
            roe_pct = float(roe) * 100
            roe_score = max(0, min(100, (roe_pct - 5) * 6.67))
            scores.append(roe_score)
            breakdown["roe_score"] = round(roe_score, 2)

        # ROA scoring
        roa = ratios.get("return_on_assets")
        if roa:
            # Benchmark: ROA > 10% = 100, ROA = 5% = 50, ROA < 2% = 0
            roa_pct = float(roa) * 100
            roa_score = max(0, min(100, (roa_pct - 2) * 12.5))
            scores.append(roa_score)
            breakdown["roa_score"] = round(roa_score, 2)

        # Net Profit Margin scoring
        npm = ratios.get("net_profit_margin")
        if npm:
            # Benchmark: NPM > 15% = 100, NPM = 7% = 50, NPM < 3% = 0
            npm_pct = float(npm) * 100
            npm_score = max(0, min(100, (npm_pct - 3) * 8.33))
            scores.append(npm_score)
            breakdown["net_margin_score"] = round(npm_score, 2)

        # Operating Margin scoring
        om = ratios.get("operating_profit_margin")
        if om:
            # Benchmark: OM > 20% = 100, OM = 10% = 50, OM < 5% = 0
            om_pct = float(om) * 100
            om_score = max(0, min(100, (om_pct - 5) * 6.67))
            scores.append(om_score)
            breakdown["operating_margin_score"] = round(om_score, 2)

        final_score = sum(scores) / len(scores) if scores else 0
        return final_score, breakdown

    async def calculate_growth_score(
        self,
        company_id: UUID,
        ratios: Dict[str, Decimal],
    ) -> Tuple[float, Dict[str, any]]:
        """
        Calculate growth score (0-100).

        Considers:
        - Revenue growth
        - Earnings growth
        - Book value growth

        Args:
            company_id: Company UUID
            ratios: Dictionary of ratio values

        Returns:
            Tuple of (score, breakdown)
        """
        scores = []
        breakdown = {}

        # Revenue growth scoring
        revenue_growth = ratios.get("revenue_growth_rate")
        if revenue_growth:
            # Benchmark: Growth > 20% = 100, Growth = 10% = 50, Growth < 0% = 0
            growth_pct = float(revenue_growth) * 100
            rev_score = max(0, min(100, growth_pct * 5))
            scores.append(rev_score)
            breakdown["revenue_growth_score"] = round(rev_score, 2)

        # Earnings growth scoring
        earnings_growth = ratios.get("earnings_growth_rate")
        if earnings_growth:
            # Benchmark: Growth > 25% = 100, Growth = 12% = 50, Growth < 0% = 0
            growth_pct = float(earnings_growth) * 100
            earn_score = max(0, min(100, growth_pct * 4))
            scores.append(earn_score)
            breakdown["earnings_growth_score"] = round(earn_score, 2)

        # Book value growth
        bv_growth = ratios.get("book_value_growth_rate")
        if bv_growth:
            # Benchmark: Growth > 15% = 100, Growth = 7% = 50, Growth < 0% = 0
            growth_pct = float(bv_growth) * 100
            bv_score = max(0, min(100, growth_pct * 6.67))
            scores.append(bv_score)
            breakdown["book_value_growth_score"] = round(bv_score, 2)

        final_score = sum(scores) / len(scores) if scores else 0
        return final_score, breakdown

    async def calculate_financial_health_score(
        self,
        company_id: UUID,
        ratios: Dict[str, Decimal],
    ) -> Tuple[float, Dict[str, any]]:
        """
        Calculate financial health score (0-100).

        Considers:
        - Current ratio (liquidity)
        - Quick ratio
        - Debt-to-equity ratio
        - Interest coverage

        Args:
            company_id: Company UUID
            ratios: Dictionary of ratio values

        Returns:
            Tuple of (score, breakdown)
        """
        scores = []
        breakdown = {}

        # Current ratio scoring
        current_ratio = ratios.get("current_ratio")
        if current_ratio:
            # Benchmark: CR > 2 = 100, CR = 1.5 = 75, CR = 1 = 50, CR < 0.8 = 0
            cr_value = float(current_ratio)
            if cr_value >= 2:
                cr_score = 100
            elif cr_value >= 1:
                cr_score = 50 + (cr_value - 1) * 50
            else:
                cr_score = max(0, cr_value * 62.5)
            scores.append(cr_score)
            breakdown["current_ratio_score"] = round(cr_score, 2)

        # Quick ratio scoring
        quick_ratio = ratios.get("quick_ratio")
        if quick_ratio:
            # Benchmark: QR > 1.5 = 100, QR = 1 = 75, QR = 0.7 = 50, QR < 0.5 = 0
            qr_value = float(quick_ratio)
            if qr_value >= 1.5:
                qr_score = 100
            elif qr_value >= 1:
                qr_score = 75 + (qr_value - 1) * 50
            else:
                qr_score = max(0, qr_value * 71.43)
            scores.append(qr_score)
            breakdown["quick_ratio_score"] = round(qr_score, 2)

        # Debt-to-equity scoring (lower is better)
        de_ratio = ratios.get("debt_to_equity_ratio")
        if de_ratio:
            # Benchmark: D/E < 0.5 = 100, D/E = 1 = 60, D/E = 2 = 20, D/E > 3 = 0
            de_value = float(de_ratio)
            de_score = max(0, min(100, 100 - de_value * 33.33))
            scores.append(de_score)
            breakdown["debt_to_equity_score"] = round(de_score, 2)

        # Interest coverage scoring
        interest_coverage = ratios.get("interest_coverage_ratio")
        if interest_coverage:
            # Benchmark: IC > 10 = 100, IC = 5 = 75, IC = 2 = 50, IC < 1 = 0
            ic_value = float(interest_coverage)
            if ic_value >= 10:
                ic_score = 100
            elif ic_value >= 2:
                ic_score = 50 + (ic_value - 2) * 6.25
            else:
                ic_score = max(0, ic_value * 50)
            scores.append(ic_score)
            breakdown["interest_coverage_score"] = round(ic_score, 2)

        final_score = sum(scores) / len(scores) if scores else 0
        return final_score, breakdown

    async def calculate_risk_score(
        self,
        company_id: UUID,
    ) -> Tuple[float, Dict[str, any]]:
        """
        Calculate risk score (0-100, higher = lower risk).

        Considers:
        - Altman Z-Score
        - Beta
        - Volatility

        Args:
            company_id: Company UUID

        Returns:
            Tuple of (score, breakdown)
        """
        scores = []
        breakdown = {}

        try:
            # Get Altman Z-Score
            z_score = await self.risk_service.calculate_altman_z_score(company_id)
            if z_score:
                # Benchmark: Z > 2.99 = 100, Z = 1.81 = 50, Z < 1.23 = 0
                if z_score >= 2.99:
                    z_score_points = 100
                elif z_score >= 1.81:
                    z_score_points = 50 + (z_score - 1.81) * 42.37
                else:
                    z_score_points = max(0, z_score * 40.65)
                scores.append(z_score_points)
                breakdown["altman_z_score"] = round(z_score_points, 2)

            # Get Beta (lower = lower risk)
            beta = await self.risk_service.calculate_beta(company_id)
            if beta:
                # Benchmark: Beta < 0.8 = 100, Beta = 1 = 75, Beta = 1.5 = 25, Beta > 2 = 0
                beta_value = float(beta)
                beta_score = max(0, min(100, 100 - abs(beta_value - 0.8) * 50))
                scores.append(beta_score)
                breakdown["beta_score"] = round(beta_score, 2)

            # Get Volatility (lower = lower risk)
            volatility_data = await self.risk_service.calculate_volatility(company_id)
            if volatility_data and "volatility_30d" in volatility_data:
                vol_30d = volatility_data["volatility_30d"]
                # Benchmark: Vol < 15% = 100, Vol = 25% = 50, Vol > 40% = 0
                vol_score = max(0, min(100, 100 - (vol_30d - 15) * 5))
                scores.append(vol_score)
                breakdown["volatility_score"] = round(vol_score, 2)

        except Exception as e:
            logger.warning(f"Error calculating risk score: {e}")

        final_score = sum(scores) / len(scores) if scores else 50  # Default to medium risk
        return final_score, breakdown

    async def calculate_composite_score(
        self,
        company_id: UUID,
    ) -> Dict[str, any]:
        """
        Calculate comprehensive composite fundamental score.

        Args:
            company_id: Company UUID

        Returns:
            Complete scoring breakdown
        """
        try:
            # Get latest ratios for the company
            ratios_dict = await self._get_latest_ratios(company_id)

            if not ratios_dict:
                raise ValueError(f"No ratios found for company {company_id}")

            # Calculate individual dimension scores
            valuation_score, valuation_breakdown = await self.calculate_valuation_score(
                company_id, ratios_dict
            )
            profitability_score, profitability_breakdown = await self.calculate_profitability_score(
                company_id, ratios_dict
            )
            growth_score, growth_breakdown = await self.calculate_growth_score(
                company_id, ratios_dict
            )
            financial_health_score, financial_health_breakdown = await self.calculate_financial_health_score(
                company_id, ratios_dict
            )
            risk_score, risk_breakdown = await self.calculate_risk_score(company_id)

            # Calculate weighted composite score
            composite_score = (
                valuation_score * self.WEIGHTS["valuation"] +
                profitability_score * self.WEIGHTS["profitability"] +
                growth_score * self.WEIGHTS["growth"] +
                financial_health_score * self.WEIGHTS["financial_health"] +
                risk_score * self.WEIGHTS["risk"]
            )

            # Determine rating
            rating = self._get_rating(composite_score)

            return {
                "status": "success",
                "company_id": str(company_id),
                "calculation_date": date.today().isoformat(),
                "composite_score": round(composite_score, 2),
                "rating": rating,
                "dimension_scores": {
                    "valuation": {
                        "score": round(valuation_score, 2),
                        "weight": self.WEIGHTS["valuation"],
                        "breakdown": valuation_breakdown,
                    },
                    "profitability": {
                        "score": round(profitability_score, 2),
                        "weight": self.WEIGHTS["profitability"],
                        "breakdown": profitability_breakdown,
                    },
                    "growth": {
                        "score": round(growth_score, 2),
                        "weight": self.WEIGHTS["growth"],
                        "breakdown": growth_breakdown,
                    },
                    "financial_health": {
                        "score": round(financial_health_score, 2),
                        "weight": self.WEIGHTS["financial_health"],
                        "breakdown": financial_health_breakdown,
                    },
                    "risk": {
                        "score": round(risk_score, 2),
                        "weight": self.WEIGHTS["risk"],
                        "breakdown": risk_breakdown,
                    },
                },
            }

        except Exception as e:
            logger.error(f"Error calculating composite score: {e}")
            raise

    async def rank_stocks(
        self,
        company_ids: Optional[List[UUID]] = None,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, any]]:
        """
        Rank multiple stocks by composite fundamental score.

        Args:
            company_ids: Optional list of company UUIDs (if None, ranks all companies)
            min_score: Optional minimum score filter

        Returns:
            List of ranked stocks
        """
        try:
            # Get companies to rank
            if company_ids:
                query = select(Company).where(
                    and_(
                        Company.tenant_id == self.tenant_id,
                        Company.id.in_(company_ids)
                    )
                )
            else:
                query = select(Company).where(Company.tenant_id == self.tenant_id)

            result = await self.db.execute(query)
            companies = result.scalars().all()

            # Calculate scores for all companies
            ranked_stocks = []
            for company in companies:
                try:
                    score_data = await self.calculate_composite_score(company.id)
                    
                    # Apply minimum score filter
                    if min_score and score_data["composite_score"] < min_score:
                        continue

                    ranked_stocks.append({
                        "company_id": str(company.id),
                        "ticker": company.ticker,
                        "company_name": company.company_name,
                        "composite_score": score_data["composite_score"],
                        "rating": score_data["rating"],
                        "dimension_scores": {
                            k: v["score"] 
                            for k, v in score_data["dimension_scores"].items()
                        },
                    })
                except Exception as e:
                    logger.warning(f"Error scoring company {company.ticker}: {e}")
                    continue

            # Sort by composite score (descending)
            ranked_stocks.sort(key=lambda x: x["composite_score"], reverse=True)

            # Add rank
            for idx, stock in enumerate(ranked_stocks, start=1):
                stock["rank"] = idx

            return ranked_stocks

        except Exception as e:
            logger.error(f"Error ranking stocks: {e}")
            raise

    async def _get_latest_ratios(self, company_id: UUID) -> Dict[str, Decimal]:
        """
        Get latest ratios for a company.

        Args:
            company_id: Company UUID

        Returns:
            Dictionary of ratio names to values
        """
        query = select(FinancialRatio).where(
            and_(
                FinancialRatio.tenant_id == self.tenant_id,
                FinancialRatio.company_id == company_id
            )
        ).order_by(FinancialRatio.period_end_date.desc())

        result = await self.db.execute(query)
        ratios = result.scalars().all()

        # Convert to dictionary (latest value for each ratio)
        ratios_dict = {}
        for ratio in ratios:
            if ratio.ratio_name not in ratios_dict:
                ratios_dict[ratio.ratio_name] = ratio.ratio_value

        return ratios_dict

    def _get_rating(self, score: float) -> str:
        """
        Convert numeric score to letter rating.

        Args:
            score: Composite score (0-100)

        Returns:
            Letter rating
        """
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C+"
        elif score >= 40:
            return "C"
        elif score >= 30:
            return "D"
        else:
            return "F"
