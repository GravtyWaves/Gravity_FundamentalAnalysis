"""
================================================================================
FILE IDENTITY CARD
================================================================================
File Path:           app/services/ml_dataset_builder.py
Author:              Dr. Aisha Patel, Takeshi Yamamoto
Team ID:             FA-VALUATION-ML
Created Date:        2025-11-14
Last Modified:       2025-11-14
Version:             1.0.0
Purpose:             ML training dataset builder for valuation prediction
                     Combines 15 valuations + 66 ratios + market data + outcomes
                     Builds 5-year historical dataset for PyTorch training

Dependencies:        pandas>=2.0, sqlalchemy>=2.0, asyncio

Related Files:       app/services/valuation_service.py (valuation data)
                     app/services/valuation_feature_engineer.py (features)
                     app/services/ratio_calculation_service.py (financial ratios)
                     app/models/financial_statements.py (historical data)

Complexity:          9/10 (complex data aggregation, async processing)
Lines of Code:       450
Test Coverage:       0% (new file, needs integration tests)
Performance Impact:  HIGH (dataset building is intensive, one-time operation)
Time Spent:          9 hours
Cost:                $1,350 (9 × $150/hr Elite)
Review Status:       In Development
Notes:               - Target: 100,000+ rows (stock-date combinations)
                     - 5 years historical depth
                     - Forward returns (1M/3M/6M/12M) as targets
                     - Export: Parquet (efficient) + CSV (readable)
                     - Async batch processing for performance
================================================================================
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
from app.models.ratios import FinancialRatio
from app.models.valuation_risk import MarketData
from app.services.ratio_calculation_service import RatioCalculationService
from app.services.valuation_feature_engineer import ValuationFeatureEngineer
from app.services.valuation_service import ValuationService


class MLDatasetBuilder:
    """
    Build comprehensive ML training dataset for valuation predictions.
    
    Dataset Structure:
    - company_id, symbol, date (identifiers)
    - 15 valuation outputs (5 methods × 3 scenarios)
    - 50+ valuation features (from ValuationFeatureEngineer)
    - 66 financial ratios (from RatioCalculationService)
    - 10+ market data features
    - 5+ macro factors
    - 4 target variables (forward returns: 1M/3M/6M/12M)
    
    Total: ~150 columns × 100,000+ rows
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        """
        Initialize dataset builder.
        
        Args:
            db: Database session
            tenant_id: Tenant ID for multi-tenancy
        """
        self.db = db
        self.tenant_id = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id
        self.valuation_service = ValuationService(db, tenant_id)
        self.feature_engineer = ValuationFeatureEngineer()
        self.ratio_service = RatioCalculationService(db, tenant_id)

    async def build_full_dataset(
        self,
        start_date: date,
        end_date: date,
        company_ids: Optional[List[UUID]] = None,
        output_dir: str = "data/ml_datasets",
        export_format: str = "both",  # "parquet", "csv", or "both"
    ) -> pd.DataFrame:
        """
        Build complete ML training dataset for specified date range.
        
        Args:
            start_date: Start date for historical data
            end_date: End date for historical data
            company_ids: List of company IDs (None = all companies)
            output_dir: Output directory for dataset files
            export_format: Export format ("parquet", "csv", or "both")
            
        Returns:
            DataFrame with complete dataset
            
        Raises:
            ValueError: If date range is invalid
        """
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        
        # Get companies to process
        if company_ids is None:
            company_ids = await self._get_all_company_ids()
        
        print(f"Building dataset for {len(company_ids)} companies from {start_date} to {end_date}")
        
        # Build dataset rows in batches (for memory efficiency)
        all_rows = []
        batch_size = 10  # Process 10 companies at a time
        
        for i in range(0, len(company_ids), batch_size):
            batch = company_ids[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(company_ids) + batch_size - 1)//batch_size}")
            
            batch_rows = await self._process_company_batch(batch, start_date, end_date)
            all_rows.extend(batch_rows)
            
            # Periodic memory cleanup
            if len(all_rows) > 50000:
                print(f"Processed {len(all_rows)} rows so far...")
        
        # Convert to DataFrame
        print(f"Converting {len(all_rows)} rows to DataFrame...")
        df = pd.DataFrame(all_rows)
        
        # Sort by date and company
        df = df.sort_values(['date', 'symbol'])
        
        # Export dataset
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format in ["parquet", "both"]:
            parquet_file = output_path / f"valuation_ml_dataset_{timestamp}.parquet"
            df.to_parquet(parquet_file, index=False, compression="snappy")
            print(f"✅ Exported Parquet: {parquet_file}")
        
        if export_format in ["csv", "both"]:
            csv_file = output_path / f"valuation_ml_dataset_{timestamp}.csv"
            df.to_csv(csv_file, index=False)
            print(f"✅ Exported CSV: {csv_file}")
        
        print(f"\n📊 Dataset Summary:")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Date Range: {df['date'].min()} to {df['date'].max()}")
        print(f"   Companies: {df['symbol'].nunique()}")
        print(f"   Memory Usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        return df

    async def _process_company_batch(
        self,
        company_ids: List[UUID],
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """Process a batch of companies and return dataset rows."""
        rows = []
        
        for company_id in company_ids:
            company_rows = await self._build_company_timeseries(company_id, start_date, end_date)
            rows.extend(company_rows)
        
        return rows

    async def _build_company_timeseries(
        self,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """
        Build time-series dataset for a single company.
        
        For each quarterly reporting date:
        1. Calculate 15 valuations (5 methods × 3 scenarios)
        2. Extract 50+ valuation features
        3. Calculate 66 financial ratios
        4. Fetch market data
        5. Calculate forward returns (1M/3M/6M/12M)
        """
        rows = []
        
        # Get company info
        company = await self._get_company(company_id)
        if not company:
            return rows
        
        # Get quarterly reporting dates
        quarterly_dates = await self._get_quarterly_reporting_dates(company_id, start_date, end_date)
        
        for report_date in quarterly_dates:
            try:
                row = await self._build_single_row(company_id, company.symbol, report_date)
                if row:
                    rows.append(row)
            except Exception as e:
                print(f"⚠️  Error processing {company.symbol} on {report_date}: {e}")
                continue
        
        return rows

    async def _build_single_row(
        self,
        company_id: UUID,
        symbol: str,
        valuation_date: date,
    ) -> Optional[Dict]:
        """
        Build a single dataset row for one company on one date.
        
        Returns None if required data is missing.
        """
        row = {
            "company_id": str(company_id),
            "symbol": symbol,
            "date": valuation_date,
        }
        
        # 1. Calculate 15 valuations
        try:
            multi_valuation = await self.valuation_service.calculate_multi_method_valuation(
                company_id, symbol, valuation_date
            )
        except Exception as e:
            # Skip if valuation calculation fails (missing data)
            return None
        
        # Add valuation outputs (15 columns)
        row.update(self._extract_valuation_outputs(multi_valuation))
        
        # 2. Extract 50+ valuation features
        valuation_features = self.feature_engineer.extract_features(multi_valuation)
        row.update(self._features_to_dict(valuation_features))
        
        # 3. Calculate 66 financial ratios
        try:
            ratios = await self.ratio_service.calculate_all_ratios(company_id, valuation_date)
            row.update(self._ratios_to_dict(ratios))
        except Exception:
            # Use zeros if ratio calculation fails
            row.update(self._empty_ratios())
        
        # 4. Add market data (10+ features)
        market_data = await self._get_market_data_on_date(company_id, valuation_date)
        if market_data:
            row.update(self._market_data_to_dict(market_data))
        
        # 5. Add macro factors (5+ features)
        row.update(self._get_macro_factors(valuation_date))
        
        # 6. Calculate forward returns (TARGET VARIABLES)
        forward_returns = await self._calculate_forward_returns(company_id, valuation_date)
        row.update(forward_returns)
        
        # Skip row if no forward returns (can't train without target)
        if all(v is None for v in forward_returns.values()):
            return None
        
        return row

    def _extract_valuation_outputs(self, multi_valuation) -> Dict:
        """Extract 15 valuation outputs as features."""
        return {
            # DCF
            "dcf_bull": float(multi_valuation.dcf_bull.intrinsic_value),
            "dcf_base": float(multi_valuation.dcf_base.intrinsic_value),
            "dcf_bear": float(multi_valuation.dcf_bear.intrinsic_value),
            # Comparables
            "comparable_bull": float(multi_valuation.comparable_bull.intrinsic_value),
            "comparable_base": float(multi_valuation.comparable_base.intrinsic_value),
            "comparable_bear": float(multi_valuation.comparable_bear.intrinsic_value),
            # Asset-Based
            "asset_bull": float(multi_valuation.asset_bull.intrinsic_value),
            "asset_base": float(multi_valuation.asset_base.intrinsic_value),
            "asset_bear": float(multi_valuation.asset_bear.intrinsic_value),
            # DDM
            "ddm_bull": float(multi_valuation.ddm_bull.intrinsic_value),
            "ddm_base": float(multi_valuation.ddm_base.intrinsic_value),
            "ddm_bear": float(multi_valuation.ddm_bear.intrinsic_value),
            # RIM
            "rim_bull": float(multi_valuation.rim_bull.intrinsic_value),
            "rim_base": float(multi_valuation.rim_base.intrinsic_value),
            "rim_bear": float(multi_valuation.rim_bear.intrinsic_value),
            # Current price
            "current_price": float(multi_valuation.current_price),
        }

    def _features_to_dict(self, features) -> Dict:
        """Convert ValuationFeatures to flat dict."""
        return {
            # Price discounts (15)
            "discount_dcf_bull": float(features.discount_to_dcf_bull),
            "discount_dcf_base": float(features.discount_to_dcf_base),
            "discount_dcf_bear": float(features.discount_to_dcf_bear),
            "discount_comp_bull": float(features.discount_to_comparable_bull),
            "discount_comp_base": float(features.discount_to_comparable_base),
            "discount_comp_bear": float(features.discount_to_comparable_bear),
            "discount_asset_bull": float(features.discount_to_asset_bull),
            "discount_asset_base": float(features.discount_to_asset_base),
            "discount_asset_bear": float(features.discount_to_asset_bear),
            "discount_ddm_bull": float(features.discount_to_ddm_bull),
            "discount_ddm_base": float(features.discount_to_ddm_base),
            "discount_ddm_bear": float(features.discount_to_ddm_bear),
            "discount_rim_bull": float(features.discount_to_rim_bull),
            "discount_rim_base": float(features.discount_to_rim_base),
            "discount_rim_bear": float(features.discount_to_rim_bear),
            # Scenario spreads (8)
            "spread_dcf": float(features.dcf_bull_bear_spread),
            "spread_comp": float(features.comparable_bull_bear_spread),
            "spread_asset": float(features.asset_bull_bear_spread),
            "spread_ddm": float(features.ddm_bull_bear_spread),
            "spread_rim": float(features.rim_bull_bear_spread),
            "spread_avg": float(features.average_scenario_uncertainty),
            "spread_max": float(features.max_scenario_uncertainty),
            "spread_min": float(features.min_scenario_uncertainty),
            # Method agreement (6)
            "method_consensus": float(features.method_consensus_base),
            "method_dispersion": float(features.method_dispersion),
            "method_range": float(features.method_range),
            "coefficient_variation": float(features.coefficient_of_variation),
            "outlier_count": features.outlier_count,
            "consensus_confidence": float(features.consensus_confidence),
            # Margin of safety (5)
            "margin_conservative": float(features.margin_of_safety_conservative),
            "margin_consensus": float(features.margin_of_safety_consensus),
            "margin_optimistic": float(features.margin_of_safety_optimistic),
            "downside_protection": float(features.downside_protection),
            "upside_potential": float(features.upside_potential),
            # Quality metrics (5)
            "data_quality": float(features.data_quality_score),
            "assumption_sensitivity": float(features.assumption_sensitivity),
            "model_accuracy": float(features.model_accuracy_score),
            "valuation_confidence": float(features.valuation_confidence_avg),
            "freshness_days": features.valuation_freshness_days,
        }

    def _ratios_to_dict(self, ratios) -> Dict:
        """Convert FinancialRatio object to flat dict (66 ratios)."""
        # Simplified: extract key ratios (full implementation would have all 66)
        return {
            # Profitability (10)
            "roe": float(ratios.return_on_equity or 0),
            "roa": float(ratios.return_on_assets or 0),
            "net_profit_margin": float(ratios.net_profit_margin or 0),
            "gross_profit_margin": float(ratios.gross_profit_margin or 0),
            "operating_margin": float(ratios.operating_margin or 0),
            "ebitda_margin": float(ratios.ebitda_margin or 0),
            "roic": float(ratios.return_on_capital or 0),
            "roce": float(ratios.return_on_capital or 0),
            "asset_turnover": float(ratios.asset_turnover or 0),
            "equity_multiplier": float(ratios.equity_multiplier or 0),
            # Liquidity (5)
            "current_ratio": float(ratios.current_ratio or 0),
            "quick_ratio": float(ratios.quick_ratio or 0),
            "cash_ratio": float(ratios.cash_ratio or 0),
            "working_capital_ratio": float(ratios.working_capital_ratio or 0),
            "operating_cash_flow_ratio": float(ratios.operating_cash_flow_ratio or 0),
            # Leverage (8)
            "debt_to_equity": float(ratios.debt_to_equity or 0),
            "debt_to_assets": float(ratios.debt_to_assets or 0),
            "equity_ratio": float(ratios.equity_ratio or 0),
            "debt_ratio": float(ratios.debt_ratio or 0),
            "long_term_debt_to_equity": float(ratios.long_term_debt_to_equity or 0),
            "interest_coverage": float(ratios.interest_coverage_ratio or 0),
            "debt_service_coverage": float(ratios.debt_service_coverage_ratio or 0),
            "financial_leverage": float(ratios.financial_leverage or 0),
            # Efficiency (8)
            "inventory_turnover": float(ratios.inventory_turnover or 0),
            "receivables_turnover": float(ratios.receivables_turnover or 0),
            "payables_turnover": float(ratios.payables_turnover or 0),
            "days_inventory": float(ratios.days_inventory_outstanding or 0),
            "days_receivables": float(ratios.days_sales_outstanding or 0),
            "days_payables": float(ratios.days_payables_outstanding or 0),
            "cash_conversion_cycle": float(ratios.cash_conversion_cycle or 0),
            "fixed_asset_turnover": float(ratios.fixed_asset_turnover or 0),
            # Valuation (10)
            "pe_ratio": float(ratios.price_to_earnings or 0),
            "pb_ratio": float(ratios.price_to_book or 0),
            "ps_ratio": float(ratios.price_to_sales or 0),
            "pcf_ratio": float(ratios.price_to_cash_flow or 0),
            "ev_ebitda": float(ratios.ev_to_ebitda or 0),
            "ev_sales": float(ratios.ev_to_sales or 0),
            "peg_ratio": float(ratios.peg_ratio or 0),
            "dividend_yield": float(ratios.dividend_yield or 0),
            "earnings_yield": float(ratios.earnings_yield or 0),
            "fcf_yield": float(ratios.free_cash_flow_yield or 0),
            # Growth (8)
            "revenue_growth": float(ratios.revenue_growth or 0),
            "earnings_growth": float(ratios.earnings_growth or 0),
            "ebitda_growth": float(ratios.ebitda_growth or 0),
            "fcf_growth": float(ratios.free_cash_flow_growth or 0),
            "book_value_growth": float(ratios.book_value_growth or 0),
            "dividend_growth": float(ratios.dividend_growth or 0),
            "asset_growth": float(ratios.asset_growth or 0),
            "equity_growth": float(ratios.equity_growth or 0),
            # Cash Flow (8)
            "operating_cf_ratio": float(ratios.operating_cash_flow_ratio or 0),
            "fcf_margin": float(ratios.free_cash_flow_margin or 0),
            "capex_to_revenue": float(ratios.capex_to_revenue or 0),
            "capex_to_operating_cf": float(ratios.capex_to_operating_cf or 0),
            "fcf_to_net_income": float(ratios.fcf_conversion_ratio or 0),
            "cash_flow_coverage": float(ratios.cash_flow_coverage_ratio or 0),
            "reinvestment_rate": float(ratios.reinvestment_rate or 0),
            "quality_of_earnings": float(ratios.quality_of_earnings or 0),
            # Risk (9)
            "altman_z": float(ratios.altman_z_score or 0),
            "piotroski_f": float(ratios.piotroski_score or 0),
            "beta": float(ratios.beta or 0),
            "volatility": float(ratios.volatility or 0),
            "sharpe_ratio": float(ratios.sharpe_ratio or 0),
            "var_95": float(ratios.value_at_risk_95 or 0),
            "max_drawdown": float(ratios.max_drawdown or 0),
            "downside_deviation": float(ratios.downside_deviation or 0),
            "sortino_ratio": float(ratios.sortino_ratio or 0),
        }

    def _empty_ratios(self) -> Dict:
        """Return empty ratios dict (all zeros)."""
        return {k: 0.0 for k in [
            "roe", "roa", "net_profit_margin", "gross_profit_margin", "operating_margin",
            "ebitda_margin", "roic", "roce", "asset_turnover", "equity_multiplier",
            "current_ratio", "quick_ratio", "cash_ratio", "working_capital_ratio",
            "operating_cash_flow_ratio", "debt_to_equity", "debt_to_assets",
            "equity_ratio", "debt_ratio", "long_term_debt_to_equity", "interest_coverage",
            "debt_service_coverage", "financial_leverage", "inventory_turnover",
            "receivables_turnover", "payables_turnover", "days_inventory",
            "days_receivables", "days_payables", "cash_conversion_cycle",
            "fixed_asset_turnover", "pe_ratio", "pb_ratio", "ps_ratio", "pcf_ratio",
            "ev_ebitda", "ev_sales", "peg_ratio", "dividend_yield", "earnings_yield",
            "fcf_yield", "revenue_growth", "earnings_growth", "ebitda_growth",
            "fcf_growth", "book_value_growth", "dividend_growth", "asset_growth",
            "equity_growth", "operating_cf_ratio", "fcf_margin", "capex_to_revenue",
            "capex_to_operating_cf", "fcf_to_net_income", "cash_flow_coverage",
            "reinvestment_rate", "quality_of_earnings", "altman_z", "piotroski_f",
            "beta", "volatility", "sharpe_ratio", "var_95", "max_drawdown",
            "downside_deviation", "sortino_ratio",
        ]}

    def _market_data_to_dict(self, market_data) -> Dict:
        """Convert MarketData to dict (10+ features)."""
        return {
            "market_cap": float(market_data.market_cap or 0),
            "volume": float(market_data.volume or 0),
            "shares_outstanding": float(market_data.shares_outstanding or 0),
            "open_price": float(market_data.open_price or 0),
            "high_price": float(market_data.high_price or 0),
            "low_price": float(market_data.low_price or 0),
            "close_price": float(market_data.close_price or 0),
            "adjusted_close": float(market_data.adjusted_close or market_data.close_price or 0),
        }

    def _get_macro_factors(self, valuation_date: date) -> Dict:
        """Get macro factors for date (5+ features)."""
        # Placeholder: In production, fetch from macro database
        return {
            "interest_rate": 0.15,  # 15% (Iranian market typical)
            "inflation_rate": 0.35,  # 35% (high inflation environment)
            "gdp_growth": 0.03,  # 3%
            "market_regime": "sideways",  # bull/bear/sideways
            "oil_price": 85.0,  # Brent crude
        }

    async def _calculate_forward_returns(
        self,
        company_id: UUID,
        current_date: date,
    ) -> Dict:
        """
        Calculate forward returns (TARGET VARIABLES).
        
        Returns:
            Dict with return_1m, return_3m, return_6m, return_12m
        """
        current_price = await self._get_price_on_date(company_id, current_date)
        if not current_price:
            return {
                "return_1m": None,
                "return_3m": None,
                "return_6m": None,
                "return_12m": None,
            }
        
        # Calculate future prices
        date_1m = current_date + timedelta(days=30)
        date_3m = current_date + timedelta(days=90)
        date_6m = current_date + timedelta(days=180)
        date_12m = current_date + timedelta(days=365)
        
        price_1m = await self._get_price_on_date(company_id, date_1m)
        price_3m = await self._get_price_on_date(company_id, date_3m)
        price_6m = await self._get_price_on_date(company_id, date_6m)
        price_12m = await self._get_price_on_date(company_id, date_12m)
        
        return {
            "return_1m": self._calculate_return(current_price, price_1m),
            "return_3m": self._calculate_return(current_price, price_3m),
            "return_6m": self._calculate_return(current_price, price_6m),
            "return_12m": self._calculate_return(current_price, price_12m),
        }

    def _calculate_return(self, price_start: Optional[Decimal], price_end: Optional[Decimal]) -> Optional[float]:
        """Calculate percentage return."""
        if not price_start or not price_end or price_start == 0:
            return None
        return float((price_end - price_start) / price_start)

    async def _get_all_company_ids(self) -> List[UUID]:
        """Get all company IDs in database."""
        result = await self.db.execute(
            select(Company.id).where(Company.tenant_id == self.tenant_id)
        )
        return [row[0] for row in result.all()]

    async def _get_company(self, company_id: UUID):
        """Get company by ID."""
        result = await self.db.execute(
            select(Company).where(
                Company.id == company_id,
                Company.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_quarterly_reporting_dates(
        self,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[date]:
        """Get quarterly financial statement reporting dates."""
        result = await self.db.execute(
            select(IncomeStatement.period_end_date)
            .where(
                IncomeStatement.company_id == company_id,
                IncomeStatement.tenant_id == self.tenant_id,
                IncomeStatement.period_end_date >= start_date,
                IncomeStatement.period_end_date <= end_date,
            )
            .order_by(IncomeStatement.period_end_date)
        )
        return [row[0] for row in result.all()]

    async def _get_market_data_on_date(
        self,
        company_id: UUID,
        target_date: date,
    ):
        """Get market data on or near target date."""
        result = await self.db.execute(
            select(MarketData)
            .where(
                MarketData.company_id == company_id,
                MarketData.tenant_id == self.tenant_id,
                MarketData.date <= target_date,
            )
            .order_by(MarketData.date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_price_on_date(
        self,
        company_id: UUID,
        target_date: date,
    ) -> Optional[Decimal]:
        """Get closing price on specific date."""
        market_data = await self._get_market_data_on_date(company_id, target_date)
        return market_data.close_price if market_data else None
