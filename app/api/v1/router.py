"""
API v1 router configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import companies, financial_statements, ratios, valuations

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(companies.router)
api_router.include_router(financial_statements.router)
api_router.include_router(ratios.router)
api_router.include_router(valuations.router)

# Additional routers will be added here:
# api_router.include_router(risk_assessments.router)
# api_router.include_router(market_data.router)
