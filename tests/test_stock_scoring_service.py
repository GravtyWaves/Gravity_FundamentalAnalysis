"""
Unit tests for StockScoringService.

Tests comprehensive fundamental scoring system covering:
- Valuation scoring (P/E, P/B, PEG, EV/EBITDA)
- Profitability scoring (ROE, ROA, margins)
- Growth scoring (revenue, earnings, book value)
- Financial health scoring (liquidity, debt, coverage)
- Risk scoring (Z-Score, beta, volatility)
- Composite scoring and letter ratings
- Multi-stock ranking
"""
# pyright: reportArgumentType=false
# type: ignore - Column[UUID] vs UUID type issues in tests

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.stock_scoring_service import StockScoringService
from app.models.company import Company
from app.models.ratios import FinancialRatio


@pytest.fixture
async def company(test_db: AsyncSession, test_tenant_id: str) -> Company:
    """Create a test company."""
    company = Company(
        id=uuid4(),
        ticker="SCORE",
        name_en="Scoring Test Company",
        name_fa="شرکت تست امتیازدهی",
        sector_en="Technology",
        sector_fa="فناوری",
        industry_en="Software",
        industry_fa="نرم‌افزار",
        tenant_id=test_tenant_id,
        is_active=True
    )
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    return company


@pytest.fixture
async def excellent_ratios(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> list[FinancialRatio]:
    """Create excellent FinancialRatio values for high score."""
    ratio_data = {
        # Valuation (excellent = low multiples)
        "price_to_earnings_ratio": Decimal("12.00"),  # < 15 = excellent
        "price_to_book_ratio": Decimal("0.80"),  # < 1 = excellent
        "peg_ratio": Decimal("0.80"),  # < 1 = excellent
        "ev_to_ebitda_ratio": Decimal("6.00"),  # < 8 = excellent
        
        # Profitability (excellent = high returns)
        "return_on_equity": Decimal("0.25"),  # 25% = excellent
        "return_on_assets": Decimal("0.12"),  # 12% = excellent
        "net_profit_margin": Decimal("0.18"),  # 18% = excellent
        "operating_profit_margin": Decimal("0.22"),  # 22% = excellent
        
        # Growth (excellent = high growth)
        "revenue_growth_rate": Decimal("0.25"),  # 25% = excellent
        "earnings_growth_rate": Decimal("0.30"),  # 30% = excellent
        "book_value_growth_rate": Decimal("0.18"),  # 18% = excellent
        
        # Financial Health (excellent = strong balance sheet)
        "current_ratio": Decimal("2.50"),  # > 2 = excellent
        "quick_ratio": Decimal("1.80"),  # > 1.5 = excellent
        "debt_to_equity_ratio": Decimal("0.30"),  # < 0.5 = excellent
        "interest_coverage_ratio": Decimal("15.00"),  # > 10 = excellent
    }
    
    ratios = []
    for ratio_name, ratio_value in ratio_data.items():
        FinancialRatio = FinancialRatio(
            id=uuid4(),
            company_id=company.id,
            ratio_name=ratio_name,
            ratio_value=ratio_value,
            period_end_date=date(2023, 12, 31),
            fiscal_year=2023,
            fiscal_period="FY",
            tenant_id=test_tenant_id
        )
        test_db.add(FinancialRatio)
        ratios.append(FinancialRatio)
    
    await test_db.commit()
    for FinancialRatio in ratios:
        await test_db.refresh(FinancialRatio)
    
    return ratios


@pytest.fixture
async def poor_ratios(
    test_db: AsyncSession,
    company: Company,
    test_tenant_id: str
) -> list[FinancialRatio]:
    """Create poor FinancialRatio values for low score."""
    ratio_data = {
        # Valuation (poor = high multiples)
        "price_to_earnings_ratio": Decimal("45.00"),  # > 40 = poor
        "price_to_book_ratio": Decimal("6.00"),  # > 5 = poor
        "peg_ratio": Decimal("3.50"),  # > 3 = poor
        "ev_to_ebitda_ratio": Decimal("20.00"),  # > 18 = poor
        
        # Profitability (poor = low returns)
        "return_on_equity": Decimal("0.03"),  # 3% = poor
        "return_on_assets": Decimal("0.01"),  # 1% = poor
        "net_profit_margin": Decimal("0.02"),  # 2% = poor
        "operating_profit_margin": Decimal("0.03"),  # 3% = poor
        
        # Growth (poor = negative/low growth)
        "revenue_growth_rate": Decimal("-0.05"),  # -5% = poor
        "earnings_growth_rate": Decimal("-0.10"),  # -10% = poor
        "book_value_growth_rate": Decimal("-0.03"),  # -3% = poor
        
        # Financial Health (poor = weak balance sheet)
        "current_ratio": Decimal("0.70"),  # < 0.8 = poor
        "quick_ratio": Decimal("0.40"),  # < 0.5 = poor
        "debt_to_equity_ratio": Decimal("3.50"),  # > 3 = poor
        "interest_coverage_ratio": Decimal("0.80"),  # < 1 = poor
    }
    
    ratios = []
    for ratio_name, ratio_value in ratio_data.items():
        FinancialRatio = FinancialRatio(
            id=uuid4(),
            company_id=company.id,
            ratio_name=ratio_name,
            ratio_value=ratio_value,
            period_end_date=date(2023, 12, 31),
            fiscal_year=2023,
            fiscal_period="FY",
            tenant_id=test_tenant_id
        )
        test_db.add(FinancialRatio)
        ratios.append(FinancialRatio)
    
    await test_db.commit()
    for FinancialRatio in ratios:
        await test_db.refresh(FinancialRatio)
    
    return ratios


@pytest.fixture
def scoring_service(test_db: AsyncSession, test_tenant_id: str) -> StockScoringService:
    """Create scoring service instance."""
    return StockScoringService(db=test_db, tenant_id=test_tenant_id)


class TestValuationScoring:
    """Test valuation dimension scoring."""

    @pytest.mark.asyncio
    async def test_valuation_score_excellent(
        self,
        scoring_service: StockScoringService,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test valuation score with excellent ratios."""
        ratios_dict = await scoring_service._get_latest_ratios(company.id)
        
        score, breakdown = await scoring_service.calculate_valuation_score(
            company.id,
            ratios_dict
        )
        
        # Excellent valuation should score high (80+)
        assert score >= 80
        assert "pe_score" in breakdown
        assert "pb_score" in breakdown
        assert "peg_score" in breakdown
        assert "ev_ebitda_score" in breakdown

    @pytest.mark.asyncio
    async def test_valuation_score_poor(
        self,
        test_db: AsyncSession,
        test_tenant_id: str,
        poor_ratios: list[FinancialRatio]
    ):
        """Test valuation score with poor ratios."""
        # Create new company for poor ratios
        company2 = Company(
            id=uuid4(),
            ticker="POOR",
            name_en="Poor Company",
            name_fa="شرکت ضعیف",
            sector_en="Technology",
            sector_fa="فناوری",
            industry_en="Software",
            industry_fa="نرم‌افزار",
            tenant_id=test_tenant_id,
            is_active=True
        )
        test_db.add(company2)
        await test_db.commit()
        await test_db.refresh(company2)
        
        # Update ratios to belong to company2
        for FinancialRatio in poor_ratios:
            FinancialRatio.company_id = company2.id
        await test_db.commit()
        
        service = StockScoringService(db=test_db, tenant_id=test_tenant_id)
        ratios_dict = await service._get_latest_ratios(company2.id)
        
        score, breakdown = await service.calculate_valuation_score(
            company2.id,
            ratios_dict
        )
        
        # Poor valuation should score low (< 20)
        assert score < 20

    @pytest.mark.asyncio
    async def test_valuation_score_missing_ratios(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test valuation score with missing ratios."""
        ratios_dict = {}  # Empty ratios
        
        score, breakdown = await scoring_service.calculate_valuation_score(
            company.id,
            ratios_dict
        )
        
        # Missing ratios should return 0
        assert score == 0
        assert len(breakdown) == 0


class TestProfitabilityScoring:
    """Test profitability dimension scoring."""

    @pytest.mark.asyncio
    async def test_profitability_score_excellent(
        self,
        scoring_service: StockScoringService,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test profitability score with excellent ratios."""
        ratios_dict = await scoring_service._get_latest_ratios(company.id)
        
        score, breakdown = await scoring_service.calculate_profitability_score(
            company.id,
            ratios_dict
        )
        
        # Excellent profitability should score high (80+)
        assert score >= 80
        assert "roe_score" in breakdown
        assert "roa_score" in breakdown
        assert "net_margin_score" in breakdown
        assert "operating_margin_score" in breakdown

    @pytest.mark.asyncio
    async def test_profitability_roe_scoring(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test ROE scoring logic."""
        # Test specific ROE values
        test_cases = [
            (Decimal("0.25"), 100),  # 25% ROE = 100 score
            (Decimal("0.10"), 33),   # 10% ROE ≈ 33 score
            (Decimal("0.05"), 0),    # 5% ROE = 0 score
        ]
        
        for roe_value, expected_score in test_cases:
            ratios = {"return_on_equity": roe_value}
            score, breakdown = await scoring_service.calculate_profitability_score(
                company.id,
                ratios
            )
            
            # Allow 10% tolerance
            assert abs(score - expected_score) < 10

    @pytest.mark.asyncio
    async def test_profitability_margins(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test margin scoring (net profit, operating)."""
        ratios = {
            "net_profit_margin": Decimal("0.20"),  # 20% = excellent
            "operating_profit_margin": Decimal("0.25"),  # 25% = excellent
        }
        
        score, breakdown = await scoring_service.calculate_profitability_score(
            company.id,
            ratios
        )
        
        # Excellent margins should score high
        assert score >= 85
        assert breakdown["net_margin_score"] >= 90
        assert breakdown["operating_margin_score"] >= 90


class TestGrowthScoring:
    """Test growth dimension scoring."""

    @pytest.mark.asyncio
    async def test_growth_score_excellent(
        self,
        scoring_service: StockScoringService,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test growth score with excellent growth rates."""
        ratios_dict = await scoring_service._get_latest_ratios(company.id)
        
        score, breakdown = await scoring_service.calculate_growth_score(
            company.id,
            ratios_dict
        )
        
        # Excellent growth should score high (80+)
        assert score >= 80
        assert "revenue_growth_score" in breakdown
        assert "earnings_growth_score" in breakdown
        assert "book_value_growth_score" in breakdown

    @pytest.mark.asyncio
    async def test_growth_negative_growth(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test growth score with negative growth rates."""
        ratios = {
            "revenue_growth_rate": Decimal("-0.10"),  # -10% growth
            "earnings_growth_rate": Decimal("-0.15"),  # -15% growth
            "book_value_growth_rate": Decimal("-0.05"),  # -5% growth
        }
        
        score, breakdown = await scoring_service.calculate_growth_score(
            company.id,
            ratios
        )
        
        # Negative growth should score 0
        assert score == 0
        assert breakdown["revenue_growth_score"] == 0
        assert breakdown["earnings_growth_score"] == 0

    @pytest.mark.asyncio
    async def test_growth_moderate(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test growth score with moderate growth rates."""
        ratios = {
            "revenue_growth_rate": Decimal("0.10"),  # 10% growth
            "earnings_growth_rate": Decimal("0.12"),  # 12% growth
        }
        
        score, breakdown = await scoring_service.calculate_growth_score(
            company.id,
            ratios
        )
        
        # Moderate growth should score mid-range (40-60)
        assert 40 <= score <= 60


class TestFinancialHealthScoring:
    """Test financial health dimension scoring."""

    @pytest.mark.asyncio
    async def test_financial_health_excellent(
        self,
        scoring_service: StockScoringService,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test financial health score with excellent ratios."""
        ratios_dict = await scoring_service._get_latest_ratios(company.id)
        
        score, breakdown = await scoring_service.calculate_financial_health_score(
            company.id,
            ratios_dict
        )
        
        # Excellent health should score high (85+)
        assert score >= 85
        assert "current_ratio_score" in breakdown
        assert "quick_ratio_score" in breakdown
        assert "debt_to_equity_score" in breakdown
        assert "interest_coverage_score" in breakdown

    @pytest.mark.asyncio
    async def test_liquidity_ratios(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test liquidity FinancialRatio scoring (current, quick)."""
        ratios = {
            "current_ratio": Decimal("2.50"),  # Excellent
            "quick_ratio": Decimal("1.80"),  # Excellent
        }
        
        score, breakdown = await scoring_service.calculate_financial_health_score(
            company.id,
            ratios
        )
        
        # Excellent liquidity = high scores
        assert breakdown["current_ratio_score"] == 100
        assert breakdown["quick_ratio_score"] == 100

    @pytest.mark.asyncio
    async def test_debt_scoring(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test debt-to-equity scoring (lower is better)."""
        test_cases = [
            (Decimal("0.30"), 90),   # Low debt = high score
            (Decimal("1.00"), 67),   # Moderate debt = medium score
            (Decimal("3.00"), 0),    # High debt = low score
        ]
        
        for de_ratio, expected_score in test_cases:
            ratios = {"debt_to_equity_ratio": de_ratio}
            score, breakdown = await scoring_service.calculate_financial_health_score(
                company.id,
                ratios
            )
            
            # Allow 15% tolerance
            assert abs(breakdown["debt_to_equity_score"] - expected_score) < 15

    @pytest.mark.asyncio
    async def test_interest_coverage(
        self,
        scoring_service: StockScoringService,
        company: Company
    ):
        """Test interest coverage scoring."""
        ratios = {
            "interest_coverage_ratio": Decimal("15.00"),  # Excellent coverage
        }
        
        score, breakdown = await scoring_service.calculate_financial_health_score(
            company.id,
            ratios
        )
        
        # Excellent coverage should score 100
        assert breakdown["interest_coverage_score"] == 100


class TestCompositeScoring:
    """Test composite score calculation."""

    @pytest.mark.asyncio
    async def test_composite_score_structure(
        self,
        scoring_service: StockScoringService,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test composite score structure and content."""
        result = await scoring_service.calculate_composite_score(company.id)
        
        # Verify structure
        assert result["status"] == "success"
        assert "company_id" in result
        assert "calculation_date" in result
        assert "composite_score" in result
        assert "rating" in result
        assert "dimension_scores" in result
        
        # Verify all dimensions present
        dimensions = result["dimension_scores"]
        assert "valuation" in dimensions
        assert "profitability" in dimensions
        assert "growth" in dimensions
        assert "financial_health" in dimensions
        assert "risk" in dimensions
        
        # Verify weights sum to 1.0
        total_weight = sum(dim["weight"] for dim in dimensions.values())
        assert abs(total_weight - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_composite_score_excellent(
        self,
        scoring_service: StockScoringService,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test composite score with excellent ratios."""
        result = await scoring_service.calculate_composite_score(company.id)
        
        # Excellent ratios should result in high composite score
        assert result["composite_score"] >= 70
        
        # Should get A- or better rating
        assert result["rating"] in ["A+", "A", "B+"]

    @pytest.mark.asyncio
    async def test_weighted_calculation(
        self,
        scoring_service: StockScoringService,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test weighted composite calculation."""
        result = await scoring_service.calculate_composite_score(company.id)
        
        # Manually calculate weighted score
        dimensions = result["dimension_scores"]
        manual_score = (
            dimensions["valuation"]["score"] * dimensions["valuation"]["weight"] +
            dimensions["profitability"]["score"] * dimensions["profitability"]["weight"] +
            dimensions["growth"]["score"] * dimensions["growth"]["weight"] +
            dimensions["financial_health"]["score"] * dimensions["financial_health"]["weight"] +
            dimensions["risk"]["score"] * dimensions["risk"]["weight"]
        )
        
        # Should match composite score
        assert abs(result["composite_score"] - manual_score) < 0.1


class TestRatingSystem:
    """Test letter rating assignment."""

    def test_rating_a_plus(self, scoring_service: StockScoringService):
        """Test A+ rating (90-100)."""
        rating = scoring_service._get_rating(95)
        assert rating == "A+"

    def test_rating_a(self, scoring_service: StockScoringService):
        """Test A rating (80-89)."""
        rating = scoring_service._get_rating(85)
        assert rating == "A"

    def test_rating_b_plus(self, scoring_service: StockScoringService):
        """Test B+ rating (70-79)."""
        rating = scoring_service._get_rating(75)
        assert rating == "B+"

    def test_rating_b(self, scoring_service: StockScoringService):
        """Test B rating (60-69)."""
        rating = scoring_service._get_rating(65)
        assert rating == "B"

    def test_rating_c_plus(self, scoring_service: StockScoringService):
        """Test C+ rating (50-59)."""
        rating = scoring_service._get_rating(55)
        assert rating == "C+"

    def test_rating_c(self, scoring_service: StockScoringService):
        """Test C rating (40-49)."""
        rating = scoring_service._get_rating(45)
        assert rating == "C"

    def test_rating_d(self, scoring_service: StockScoringService):
        """Test D rating (30-39)."""
        rating = scoring_service._get_rating(35)
        assert rating == "D"

    def test_rating_f(self, scoring_service: StockScoringService):
        """Test F rating (0-29)."""
        rating = scoring_service._get_rating(25)
        assert rating == "F"

    def test_rating_edge_cases(self, scoring_service: StockScoringService):
        """Test rating edge cases."""
        assert scoring_service._get_rating(90) == "A+"
        assert scoring_service._get_rating(89.9) == "A"
        assert scoring_service._get_rating(80) == "A"
        assert scoring_service._get_rating(79.9) == "B+"


@pytest.mark.asyncio
class TestStockRanking:
    """Test multi-stock ranking functionality."""

    async def test_rank_multiple_stocks(
        self,
        test_db: AsyncSession,
        test_tenant_id: str,
        excellent_ratios: list[FinancialRatio],
        poor_ratios: list[FinancialRatio]
    ):
        """Test ranking multiple stocks."""
        # Create companies with different scores
        companies = []
        for i in range(3):
            company = Company(
                id=uuid4(),
                ticker=f"RANK{i}",
                name_en=f"Rank Company {i}",
                name_fa=f"شرکت رنک {i}",
                sector_en="Technology",
                sector_fa="فناوری",
                industry_en="Software",
                industry_fa="نرم‌افزار",
                tenant_id=test_tenant_id,
                is_active=True
            )
            test_db.add(company)
            companies.append(company)
        
        await test_db.commit()
        for company in companies:
            await test_db.refresh(company)
        
        # Assign ratios to companies
        for FinancialRatio in excellent_ratios:
            FinancialRatio.company_id = companies[0].id
        
        for FinancialRatio in poor_ratios:
            FinancialRatio.company_id = companies[1].id
        
        await test_db.commit()
        
        # Rank stocks
        service = StockScoringService(db=test_db, tenant_id=test_tenant_id)
        ranked = await service.rank_stocks()
        
        # Verify ranking structure
        assert len(ranked) >= 2
        assert all("rank" in stock for stock in ranked)
        assert all("composite_score" in stock for stock in ranked)
        
        # Verify descending order
        for i in range(len(ranked) - 1):
            assert ranked[i]["composite_score"] >= ranked[i + 1]["composite_score"]
        
        # Verify ranks are sequential
        for i, stock in enumerate(ranked, start=1):
            assert stock["rank"] == i

    async def test_rank_with_min_score_filter(
        self,
        test_db: AsyncSession,
        test_tenant_id: str,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test ranking with minimum score filter."""
        service = StockScoringService(db=test_db, tenant_id=test_tenant_id)
        
        # Rank with high minimum score
        ranked = await service.rank_stocks(min_score=80.0)
        
        # All results should be >= min_score
        for stock in ranked:
            assert stock["composite_score"] >= 80.0

    async def test_rank_specific_companies(
        self,
        test_db: AsyncSession,
        test_tenant_id: str,
        company: Company,
        excellent_ratios: list[FinancialRatio]
    ):
        """Test ranking specific companies only."""
        service = StockScoringService(db=test_db, tenant_id=test_tenant_id)
        
        # Rank only specific company
        ranked = await service.rank_stocks(company_ids=[company.id])
        
        # Should only return requested company
        assert len(ranked) == 1
        assert ranked[0]["ticker"] == "SCORE"


@pytest.mark.asyncio
class TestMultiTenancy:
    """Test multi-tenancy isolation."""

    async def test_scoring_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        excellent_ratios: list[FinancialRatio],
        test_tenant_id: str
    ):
        """Test scoring respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = StockScoringService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should not find ratios from different tenant
        with pytest.raises(ValueError, match="No ratios found"):
            await service_other_tenant.calculate_composite_score(company.id)

    async def test_ranking_tenant_isolation(
        self,
        test_db: AsyncSession,
        company: Company,
        excellent_ratios: list[FinancialRatio],
        test_tenant_id: str
    ):
        """Test ranking respects tenant isolation."""
        # Service for different tenant
        different_tenant = str(uuid4())
        service_other_tenant = StockScoringService(
            db=test_db,
            tenant_id=different_tenant
        )
        
        # Should not find companies from different tenant
        ranked = await service_other_tenant.rank_stocks()
        
        # Should return empty list (no companies in different tenant)
        assert len(ranked) == 0
