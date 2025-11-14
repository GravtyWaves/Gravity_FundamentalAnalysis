"""
Celery configuration for scheduled tasks.

Configures Celery with Redis broker and result backend.
Defines periodic task schedules for daily score calculation,
weekly weight optimization, and monthly model retraining.
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "fundamental_analysis",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_backend_transport_options={
        "master_name": "mymaster",
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Queue configuration
    task_default_queue="fundamental_analysis",
    task_queues=(
        Queue(
            "fundamental_analysis",
            Exchange("fundamental_analysis"),
            routing_key="fundamental_analysis",
        ),
        Queue(
            "ml_training",
            Exchange("ml_training"),
            routing_key="ml_training",
            priority=5,  # Higher priority for ML tasks
        ),
    ),
)

# Import tasks (must be after celery_app initialization)
from app.tasks import scoring_tasks  # noqa: F401

# Periodic task schedule
celery_app.conf.beat_schedule = {
    # Daily score calculation (every day at 1:00 AM UTC)
    "daily-score-calculation": {
        "task": "calculate_daily_scores",
        "schedule": crontab(hour=1, minute=0),
        "args": (settings.default_tenant_id,),
        "options": {
            "queue": "fundamental_analysis",
            "priority": 8,
        },
    },
    
    # Weekly weight optimization (every Sunday at 2:00 AM UTC)
    "weekly-weight-optimization": {
        "task": "optimize_ml_weights",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
        "args": (settings.default_tenant_id,),
        "options": {
            "queue": "ml_training",
            "priority": 5,
        },
    },
    
    # Monthly model retraining (first day of month at 3:00 AM UTC)
    "monthly-model-retraining": {
        "task": "retrain_ml_model",
        "schedule": crontab(hour=3, minute=0, day_of_month=1),
        "args": (settings.default_tenant_id,),
        "options": {
            "queue": "ml_training",
            "priority": 10,  # Highest priority
        },
    },
}

# Task routing
celery_app.conf.task_routes = {
    "calculate_daily_scores": {"queue": "fundamental_analysis"},
    "optimize_ml_weights": {"queue": "ml_training"},
    "retrain_ml_model": {"queue": "ml_training"},
}
