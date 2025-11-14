"""
Trend Analysis Service.

Comprehensive trend analysis for financial metrics including:
- Revenue trends
- Profitability trends
- Ratio trends
- Growth analysis (CAGR)
- Linear regression
- Moving averages
- Anomaly detection
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np
from scipy import stats

from app.models.company import Company
from app.models.financial_statements import IncomeStatement, BalanceSheet
from app.models.ratios import FinancialRatio

logger = logging.getLogger(__name__)


class TrendAnalysisService:
    """Service for trend analysis of financial metrics."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize trend analysis service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    def calculate_cagr(
        self,
        start_value: Decimal,
        end_value: Decimal,
        num_years: int,
    ) -> Optional[Decimal]:
        """
        Calculate Compound Annual Growth Rate (CAGR).

        Formula: CAGR = (End Value / Start Value)^(1/n) - 1

        Args:
            start_value: Starting value
            end_value: Ending value
            num_years: Number of years

        Returns:
            CAGR as decimal or None if invalid
        """
        if start_value <= 0 or end_value <= 0 or num_years <= 0:
            return None

        try:
            start_float = float(start_value)
            end_float = float(end_value)

            cagr = (end_float / start_float) ** (1 / num_years) - 1
            return Decimal(str(round(cagr, 6)))

        except Exception as e:
            logger.error(f"Error calculating CAGR: {e}")
            return None

    def linear_regression(
        self,
        data_points: List[Tuple[float, float]],
    ) -> Dict[str, float]:
        """
        Perform linear regression on data points.

        Args:
            data_points: List of (x, y) tuples

        Returns:
            Dictionary with slope, intercept, r_squared, p_value
        """
        if len(data_points) < 2:
            return {
                "slope": 0.0,
                "intercept": 0.0,
                "r_squared": 0.0,
                "p_value": 1.0,
                "trend": "insufficient_data",
            }

        x_values = np.array([point[0] for point in data_points])
        y_values = np.array([point[1] for point in data_points])

        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_values, y_values)

        # Determine trend direction
        if p_value < 0.05:  # Statistically significant
            if slope > 0:
                trend = "improving"
            else:
                trend = "declining"
        else:
            trend = "stable"

        return {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_value ** 2),
            "p_value": float(p_value),
            "std_error": float(std_err),
            "trend": trend,
            "significance": "significant" if p_value < 0.05 else "not_significant",
        }

    def calculate_moving_average(
        self,
        values: List[float],
        window: int = 3,
    ) -> List[float]:
        """
        Calculate moving average.

        Args:
            values: List of values
            window: Window size for moving average

        Returns:
            List of moving averages
        """
        if len(values) < window:
            return values

        moving_avgs = []
        for i in range(len(values)):
            if i < window - 1:
                moving_avgs.append(values[i])
            else:
                avg = sum(values[i-window+1:i+1]) / window
                moving_avgs.append(avg)

        return moving_avgs

    def detect_anomalies(
        self,
        values: List[float],
        threshold_std: float = 2.0,
    ) -> List[Dict[str, any]]:
        """
        Detect anomalies using statistical methods.

        Args:
            values: List of values
            threshold_std: Number of standard deviations for anomaly threshold

        Returns:
            List of anomalies with indices and values
        """
        if len(values) < 3:
            return []

        mean = np.mean(values)
        std = np.std(values)

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std) if std > 0 else 0
            if z_score > threshold_std:
                anomalies.append({
                    "index": i,
                    "value": value,
                    "z_score": float(z_score),
                    "deviation": float(abs(value - mean)),
                    "type": "outlier_high" if value > mean else "outlier_low",
                })

        return anomalies

    async def analyze_revenue_trend(
        self,
        company_id: UUID,
        num_years: Optional[int] = 5,
    ) -> Dict[str, any]:
        """
        Analyze revenue trend.

        Args:
            company_id: Company UUID
            num_years: Number of years to analyze

        Returns:
            Revenue trend analysis
        """
        try:
            # Fetch historical income statements
            query = select(IncomeStatement).where(
                and_(
                    IncomeStatement.company_id == company_id,
                    IncomeStatement.tenant_id == self.tenant_id,
                    IncomeStatement.period_type == "annual",
                )
            ).order_by(IncomeStatement.fiscal_year.desc()).limit(num_years)

            result = await self.db.execute(query)
            statements = list(result.scalars().all())

            if len(statements) < 2:
                return {
                    "status": "insufficient_data",
                    "years_available": len(statements),
                }

            # Sort by fiscal year ascending
            statements.sort(key=lambda x: x.fiscal_year)

            # Extract revenue data
            years = [stmt.fiscal_year for stmt in statements]
            revenues = [float(stmt.revenue) if stmt.revenue else 0.0 for stmt in statements]

            # Calculate CAGR
            cagr = None
            if len(revenues) >= 2 and revenues[0] > 0 and revenues[-1] > 0:
                cagr = self.calculate_cagr(
                    Decimal(str(revenues[0])),
                    Decimal(str(revenues[-1])),
                    len(revenues) - 1
                )

            # Linear regression
            data_points = [(i, revenues[i]) for i in range(len(revenues))]
            regression = self.linear_regression(data_points)

            # Moving average
            moving_avg_3y = self.calculate_moving_average(revenues, window=3)

            # YoY growth rates
            yoy_growth = []
            for i in range(1, len(revenues)):
                if revenues[i-1] > 0:
                    growth = (revenues[i] - revenues[i-1]) / revenues[i-1]
                    yoy_growth.append(growth)

            # Detect anomalies
            anomalies = self.detect_anomalies(revenues)

            return {
                "status": "success",
                "company_id": str(company_id),
                "metric": "revenue",
                "period": {
                    "start_year": years[0],
                    "end_year": years[-1],
                    "num_years": len(years),
                },
                "values": {
                    "years": years,
                    "revenues": revenues,
                    "moving_average_3y": moving_avg_3y,
                },
                "growth": {
                    "cagr": float(cagr) if cagr else None,
                    "yoy_growth": yoy_growth,
                    "average_yoy_growth": float(np.mean(yoy_growth)) if yoy_growth else None,
                },
                "regression": regression,
                "anomalies": anomalies,
                "summary": {
                    "trend_direction": regression["trend"],
                    "trend_strength": regression["r_squared"],
                    "statistical_significance": regression["significance"],
                    "consistency": "high" if regression["r_squared"] > 0.8 else "medium" if regression["r_squared"] > 0.5 else "low",
                },
            }

        except Exception as e:
            logger.error(f"Error analyzing revenue trend: {e}")
            raise

    async def analyze_profitability_trends(
        self,
        company_id: UUID,
        num_years: Optional[int] = 5,
    ) -> Dict[str, any]:
        """
        Analyze profitability trends (margins, ROE, ROA).

        Args:
            company_id: Company UUID
            num_years: Number of years to analyze

        Returns:
            Profitability trend analysis
        """
        try:
            # Fetch historical ratios
            query = select(FinancialRatio).where(
                and_(
                    FinancialRatio.company_id == company_id,
                    FinancialRatio.tenant_id == self.tenant_id,
                )
            ).order_by(FinancialRatio.calculation_date.desc()).limit(num_years)

            result = await self.db.execute(query)
            ratios = list(result.scalars().all())

            if len(ratios) < 2:
                return {
                    "status": "insufficient_data",
                    "periods_available": len(ratios),
                }

            # Sort by date ascending
            ratios.sort(key=lambda x: x.calculation_date)

            # Analyze multiple profitability metrics
            metrics = {
                "gross_margin": [float(r.gross_margin) if r.gross_margin else None for r in ratios],
                "operating_margin": [float(r.operating_margin) if r.operating_margin else None for r in ratios],
                "net_margin": [float(r.net_margin) if r.net_margin else None for r in ratios],
                "roe": [float(r.roe) if r.roe else None for r in ratios],
                "roa": [float(r.roa) if r.roa else None for r in ratios],
            }

            results = {}

            for metric_name, values in metrics.items():
                # Remove None values
                valid_values = [v for v in values if v is not None]

                if len(valid_values) < 2:
                    results[metric_name] = {"status": "insufficient_data"}
                    continue

                # Linear regression
                data_points = [(i, valid_values[i]) for i in range(len(valid_values))]
                regression = self.linear_regression(data_points)

                # Calculate change
                change = valid_values[-1] - valid_values[0]
                change_pct = (change / abs(valid_values[0])) * 100 if valid_values[0] != 0 else 0

                results[metric_name] = {
                    "values": valid_values,
                    "current": valid_values[-1],
                    "first": valid_values[0],
                    "change": float(change),
                    "change_pct": float(change_pct),
                    "average": float(np.mean(valid_values)),
                    "std_dev": float(np.std(valid_values)),
                    "regression": regression,
                    "trend": regression["trend"],
                }

            return {
                "status": "success",
                "company_id": str(company_id),
                "num_periods": len(ratios),
                "metrics": results,
                "overall_profitability_trend": self._determine_overall_trend(results),
            }

        except Exception as e:
            logger.error(f"Error analyzing profitability trends: {e}")
            raise

    def _determine_overall_trend(self, metrics_results: Dict) -> str:
        """
        Determine overall trend from multiple metrics.

        Args:
            metrics_results: Results dictionary for multiple metrics

        Returns:
            Overall trend: "improving", "declining", or "mixed"
        """
        improving = 0
        declining = 0

        for metric_name, result in metrics_results.items():
            if isinstance(result, dict) and "trend" in result:
                if result["trend"] == "improving":
                    improving += 1
                elif result["trend"] == "declining":
                    declining += 1

        if improving > declining:
            return "improving"
        elif declining > improving:
            return "declining"
        else:
            return "mixed"

    async def analyze_ratio_trend(
        self,
        company_id: UUID,
        ratio_name: str,
        num_periods: Optional[int] = 8,
    ) -> Dict[str, any]:
        """
        Analyze trend for a specific financial ratio.

        Args:
            company_id: Company UUID
            ratio_name: Ratio field name (e.g., 'current_ratio', 'debt_to_equity')
            num_periods: Number of periods to analyze

        Returns:
            Ratio trend analysis
        """
        try:
            # Fetch historical ratios
            query = select(FinancialRatio).where(
                and_(
                    FinancialRatio.company_id == company_id,
                    FinancialRatio.tenant_id == self.tenant_id,
                )
            ).order_by(FinancialRatio.calculation_date.desc()).limit(num_periods)

            result = await self.db.execute(query)
            ratios = list(result.scalars().all())

            if len(ratios) < 2:
                return {
                    "status": "insufficient_data",
                    "periods_available": len(ratios),
                }

            # Sort by date ascending
            ratios.sort(key=lambda x: x.calculation_date)

            # Extract ratio values
            dates = [r.calculation_date for r in ratios]
            values = [float(getattr(r, ratio_name)) if getattr(r, ratio_name) else None for r in ratios]

            # Remove None values
            valid_data = [(dates[i], values[i]) for i in range(len(values)) if values[i] is not None]

            if len(valid_data) < 2:
                return {
                    "status": "insufficient_data",
                    "valid_periods": len(valid_data),
                }

            valid_dates, valid_values = zip(*valid_data)

            # Linear regression
            data_points = [(i, valid_values[i]) for i in range(len(valid_values))]
            regression = self.linear_regression(data_points)

            # Moving averages
            moving_avg_3 = self.calculate_moving_average(list(valid_values), window=3)
            moving_avg_5 = self.calculate_moving_average(list(valid_values), window=5)

            # Detect anomalies
            anomalies = self.detect_anomalies(list(valid_values))

            # Calculate volatility (coefficient of variation)
            mean = np.mean(valid_values)
            std_dev = np.std(valid_values)
            cv = (std_dev / abs(mean)) if mean != 0 else 0

            return {
                "status": "success",
                "company_id": str(company_id),
                "ratio_name": ratio_name,
                "period": {
                    "start_date": valid_dates[0].isoformat(),
                    "end_date": valid_dates[-1].isoformat(),
                    "num_periods": len(valid_dates),
                },
                "values": {
                    "dates": [d.isoformat() for d in valid_dates],
                    "values": list(valid_values),
                    "moving_avg_3": moving_avg_3,
                    "moving_avg_5": moving_avg_5,
                },
                "statistics": {
                    "current": valid_values[-1],
                    "mean": float(mean),
                    "median": float(np.median(valid_values)),
                    "std_dev": float(std_dev),
                    "min": float(min(valid_values)),
                    "max": float(max(valid_values)),
                    "coefficient_of_variation": float(cv),
                },
                "regression": regression,
                "anomalies": anomalies,
                "summary": {
                    "trend_direction": regression["trend"],
                    "trend_strength": regression["r_squared"],
                    "volatility": "high" if cv > 0.3 else "medium" if cv > 0.15 else "low",
                    "consistency": "high" if regression["r_squared"] > 0.8 else "medium" if regression["r_squared"] > 0.5 else "low",
                },
            }

        except Exception as e:
            logger.error(f"Error analyzing ratio trend: {e}")
            raise
