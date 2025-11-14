"""
API v1 router configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    companies,
    data_collection,
    financial_statements,
    market_data,
    ratios,
    risk_assessments,
    scenario_analysis,
    sensitivity_analysis,
    stock_scoring,
    trend_analysis,
    value_drivers,
    valuations,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(financial_statements.router, prefix="/financial-statements", tags=["financial-statements"])
api_router.include_router(ratios.router, prefix="/ratios", tags=["ratios"])
api_router.include_router(valuations.router, prefix="/valuations", tags=["valuations"])
api_router.include_router(data_collection.router, prefix="/data-collection", tags=["data-collection"])
api_router.include_router(risk_assessments.router, prefix="/risk-assessments", tags=["risk-assessments"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(trend_analysis.router, prefix="/trend-analysis", tags=["trend-analysis"])
api_router.include_router(scenario_analysis.router, prefix="/scenario-analysis", tags=["scenario-analysis"])
api_router.include_router(sensitivity_analysis.router, prefix="/sensitivity-analysis", tags=["sensitivity-analysis"])
api_router.include_router(value_drivers.router, prefix="/value-drivers", tags=["value-drivers"])
api_router.include_router(stock_scoring.router, prefix="/stock-scoring", tags=["stock-scoring"])
