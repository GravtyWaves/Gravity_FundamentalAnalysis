"""
Celery tasks for daily stock scoring calculations.

Scheduled tasks:
- Daily score calculation for all companies
- Weekly ML weight optimization
- Monthly model retraining
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import date, datetime
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.services.stock_scoring_service import StockScoringService
from app.services.ml_weight_optimizer import MLWeightOptimizer

logger = get_task_logger(__name__)


@shared_task(name="calculate_daily_scores")
def calculate_daily_scores_task(tenant_id: str) -> dict:
    """
    Calculate fundamental scores for all companies (daily).

    Args:
        tenant_id: Tenant ID to process

    Returns:
        Task result summary
    """
    import asyncio
    return asyncio.run(_calculate_daily_scores(tenant_id))


async def _calculate_daily_scores(tenant_id: str) -> dict:
    """
    Async implementation of daily score calculation.

    Args:
        tenant_id: Tenant ID to process

    Returns:
        Dictionary with task results
    """
    logger.info(f"Starting daily score calculation for tenant: {tenant_id}")
    start_time = datetime.now()

    async with AsyncSessionLocal() as db:
        try:
            # Get all active companies
            query = select(Company).where(Company.tenant_id == tenant_id)
            result = await db.execute(query)
            companies = result.scalars().all()

            logger.info(f"Found {len(companies)} companies to process")

            # Initialize scoring service
            scoring_service = StockScoringService(db, tenant_id)

            # Calculate scores for each company
            results = {
                "success_count": 0,
                "error_count": 0,
                "errors": [],
                "company_scores": [],
            }

            for company in companies:
                try:
                    # Calculate composite score
                    score_result = await scoring_service.calculate_composite_score(company.id)

                    results["company_scores"].append({
                        "company_id": str(company.id),
                        "ticker": company.ticker,
                        "score": score_result["composite_score"],
                        "rating": score_result["rating"],
                    })

                    results["success_count"] += 1
                    logger.info(
                        f"Calculated score for {company.ticker}: "
                        f"{score_result['composite_score']:.2f} ({score_result['rating']})"
                    )

                except Exception as e:
                    results["error_count"] += 1
                    error_msg = f"Error calculating score for {company.ticker}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Prepare final result
            final_result = {
                "status": "completed",
                "tenant_id": tenant_id,
                "calculation_date": date.today().isoformat(),
                "duration_seconds": duration,
                "total_companies": len(companies),
                "success_count": results["success_count"],
                "error_count": results["error_count"],
                "errors": results["errors"][:10],  # First 10 errors only
                "average_score": (
                    sum(s["score"] for s in results["company_scores"]) / len(results["company_scores"])
                    if results["company_scores"] else 0
                ),
            }

            logger.info(
                f"Daily score calculation completed: "
                f"{results['success_count']} success, {results['error_count']} errors, "
                f"duration: {duration:.2f}s"
            )

            return final_result

        except Exception as e:
            logger.error(f"Fatal error in daily score calculation: {e}")
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": str(e),
            }


@shared_task(name="optimize_ml_weights")
def optimize_ml_weights_task(tenant_id: str, sector: str = None) -> dict:
    """
    Optimize ML-based scoring weights (weekly).

    Args:
        tenant_id: Tenant ID to process
        sector: Optional sector filter

    Returns:
        Task result summary
    """
    import asyncio
    return asyncio.run(_optimize_ml_weights(tenant_id, sector))


async def _optimize_ml_weights(tenant_id: str, sector: str = None) -> dict:
    """
    Async implementation of ML weight optimization.

    Args:
        tenant_id: Tenant ID to process
        sector: Optional sector filter

    Returns:
        Dictionary with optimization results
    """
    logger.info(f"Starting ML weight optimization for tenant: {tenant_id}")
    start_time = datetime.now()

    async with AsyncSessionLocal() as db:
        try:
            # Initialize ML optimizer
            optimizer = MLWeightOptimizer(db, tenant_id)

            # Load existing model (if available)
            await optimizer.load_model()

            # Get optimized weights (will retrain if needed)
            optimized_weights = await optimizer.get_optimized_weights(
                sector=sector,
                force_retrain=True
            )

            # Get feature importances
            importances = await optimizer.get_dimension_importance()

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "status": "completed",
                "tenant_id": tenant_id,
                "sector": sector,
                "optimization_date": date.today().isoformat(),
                "duration_seconds": duration,
                "optimized_weights": optimized_weights,
                "feature_importances": importances,
            }

            logger.info(f"ML weight optimization completed in {duration:.2f}s")
            logger.info(f"Optimized weights: {optimized_weights}")

            return result

        except Exception as e:
            logger.error(f"Error in ML weight optimization: {e}")
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": str(e),
            }


@shared_task(name="retrain_ml_model")
def retrain_ml_model_task(tenant_id: str) -> dict:
    """
    Retrain ML scoring model from scratch (monthly).

    Args:
        tenant_id: Tenant ID to process

    Returns:
        Task result summary
    """
    import asyncio
    return asyncio.run(_retrain_ml_model(tenant_id))


async def _retrain_ml_model(tenant_id: str) -> dict:
    """
    Async implementation of ML model retraining.

    Args:
        tenant_id: Tenant ID to process

    Returns:
        Dictionary with retraining results
    """
    logger.info(f"Starting ML model retraining for tenant: {tenant_id}")
    start_time = datetime.now()

    async with AsyncSessionLocal() as db:
        try:
            # Initialize ML optimizer
            optimizer = MLWeightOptimizer(db, tenant_id)

            # Force full retraining
            await optimizer._train_model(sector=None)

            # Get updated weights
            new_weights = await optimizer.get_optimized_weights(force_retrain=False)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "status": "completed",
                "tenant_id": tenant_id,
                "retraining_date": date.today().isoformat(),
                "duration_seconds": duration,
                "new_weights": new_weights,
                "training_date": optimizer.last_training_date.isoformat() if optimizer.last_training_date else None,
            }

            logger.info(f"ML model retraining completed in {duration:.2f}s")
            logger.info(f"New weights: {new_weights}")

            return result

        except Exception as e:
            logger.error(f"Error in ML model retraining: {e}")
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "error": str(e),
            }


# Celery Beat schedule configuration (add to celeryconfig.py)
CELERY_BEAT_SCHEDULE = {
    "daily-score-calculation": {
        "task": "calculate_daily_scores",
        "schedule": "0 1 * * *",  # Every day at 1:00 AM
        "args": ("default_tenant",),  # Replace with actual tenant ID
    },
    "weekly-weight-optimization": {
        "task": "optimize_ml_weights",
        "schedule": "0 2 * * 0",  # Every Sunday at 2:00 AM
        "args": ("default_tenant",),
    },
    "monthly-model-retraining": {
        "task": "retrain_ml_model",
        "schedule": "0 3 1 * *",  # First day of month at 3:00 AM
        "args": ("default_tenant",),
    },
}
