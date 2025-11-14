"""
================================================================================
FILE IDENTITY
================================================================================
File Path:           scripts/setup_database.py
Author:              Dr. Aisha Patel (Database Architect)
Team ID:             FA-DEVOPS
Created Date:        2025-11-14
Version:             1.0.0
Purpose:             Automated database setup script
                     Creates database, schema, tables, and seed data
                     ONE-COMMAND setup for production deployment

Dependencies:        psycopg2>=2.9, sqlalchemy>=2.0, alembic>=1.12

Related Files:       app/core/database.py (database connection)
                     app/models/*.py (all models)
                     alembic/versions/*.py (migrations)

Time Spent:          3 hours
Cost:                $450 (3 × $150/hr Elite)
================================================================================
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_database_if_not_exists():
    """Create PostgreSQL database if it doesn't exist."""
    
    if not settings.database_url:
        logger.info("⚠️ No DATABASE_URL provided. Skipping database creation.")
        return False
    
    try:
        # Parse database URL
        db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Extract database name
        db_name = db_url.split("/")[-1].split("?")[0]
        
        # Connection URL without database name
        conn_url = "/".join(db_url.split("/")[:-1]) + "/postgres"
        
        logger.info(f"📊 Connecting to PostgreSQL server...")
        
        # Connect to postgres database
        conn = psycopg2.connect(conn_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if exists:
            logger.info(f"✅ Database '{db_name}' already exists")
        else:
            logger.info(f"📝 Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"✅ Database '{db_name}' created successfully")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        logger.error(f"❌ Cannot connect to PostgreSQL: {e}")
        logger.info("💡 Make sure PostgreSQL is running and accessible")
        return False
    except Exception as e:
        logger.error(f"❌ Database creation failed: {e}")
        return False


async def create_schema_and_tables():
    """Create schema and all tables using SQLAlchemy models."""
    
    if not settings.database_url:
        logger.info("⚠️ No DATABASE_URL provided. Skipping schema/table creation.")
        return False
    
    try:
        logger.info("📋 Creating database schema and tables...")
        
        # Create async engine
        engine = create_async_engine(settings.database_url, echo=False)
        
        async with engine.begin() as conn:
            # Create schema
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS tse"))
            logger.info("✅ Schema 'tse' created/verified")
            
            # Import all models
            from app.models.base import BaseModel
            from app.models.company import Company
            from app.models.financial_statements import BalanceSheet, CashFlowStatement, IncomeStatement
            from app.models.ratios import FinancialRatio
            from app.models.valuation_risk import MarketData, RiskAssessment, Valuation
            from app.models.prediction_tracking import ValuationPrediction, PredictionOutcome
            from app.core.database import Base
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ All tables created successfully")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema/table creation failed: {e}")
        return False


async def run_alembic_migrations():
    """Run Alembic migrations to latest version."""
    
    if not settings.database_url:
        logger.info("⚠️ No DATABASE_URL provided. Skipping migrations.")
        return False
    
    try:
        logger.info("🔄 Running database migrations...")
        
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            logger.info("✅ Migrations completed successfully")
            return True
        else:
            logger.error(f"❌ Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        return False


async def seed_sample_data():
    """Seed sample data for testing (optional)."""
    
    if not settings.database_url:
        logger.info("⚠️ No DATABASE_URL provided. Skipping sample data.")
        return False
    
    try:
        logger.info("🌱 Seeding sample data...")
        
        from app.core.database import AsyncSessionLocal
        from app.models.company import Company
        from uuid import uuid4
        from datetime import datetime
        
        if AsyncSessionLocal is None:
            logger.warning("⚠️ Database not available. Skipping seed data.")
            return False
        
        async with AsyncSessionLocal() as session:
            # Check if data already exists
            from sqlalchemy import select
            result = await session.execute(select(Company).limit(1))
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info("✅ Sample data already exists. Skipping.")
                return True
            
            # Create sample companies
            companies = [
                Company(
                    id=uuid4(),
                    tenant_id=settings.default_tenant_id,
                    symbol="SAMPLE1",
                    name="Sample Company 1",
                    industry="Technology",
                    sector="Software",
                    is_active=True,
                    created_at=datetime.utcnow(),
                ),
                Company(
                    id=uuid4(),
                    tenant_id=settings.default_tenant_id,
                    symbol="SAMPLE2",
                    name="Sample Company 2",
                    industry="Manufacturing",
                    sector="Industrial",
                    is_active=True,
                    created_at=datetime.utcnow(),
                ),
            ]
            
            session.add_all(companies)
            await session.commit()
            
            logger.info(f"✅ Seeded {len(companies)} sample companies")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Sample data seeding failed: {e}")
        return False


async def verify_database_connection():
    """Verify database connection is working."""
    
    if not settings.database_url:
        logger.info("⚠️ No DATABASE_URL provided. Running in NO-DB mode.")
        return True  # Not an error, just no DB
    
    try:
        logger.info("🔍 Verifying database connection...")
        
        engine = create_async_engine(settings.database_url, echo=False)
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✅ PostgreSQL version: {version}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def main():
    """Main setup function."""
    
    logger.info("=" * 70)
    logger.info("🚀 GRAVITY FUNDAMENTAL ANALYSIS - DATABASE SETUP")
    logger.info("=" * 70)
    
    if not settings.database_url:
        logger.info("")
        logger.info("📝 NO DATABASE URL PROVIDED")
        logger.info("   Service will run in NO-DB mode (in-memory storage)")
        logger.info("   To enable database:")
        logger.info("   1. Set DATABASE_URL environment variable")
        logger.info("   2. Run: python scripts/setup_database.py")
        logger.info("")
        logger.info("=" * 70)
        return
    
    steps = [
        ("Step 1: Create Database", create_database_if_not_exists),
        ("Step 2: Verify Connection", verify_database_connection),
        ("Step 3: Create Schema & Tables", create_schema_and_tables),
        ("Step 4: Seed Sample Data (optional)", seed_sample_data),
    ]
    
    logger.info("")
    success_count = 0
    
    for step_name, step_func in steps:
        logger.info(f"\n{step_name}...")
        logger.info("-" * 70)
        
        if asyncio.iscoroutinefunction(step_func):
            result = await step_func()
        else:
            result = step_func()
        
        if result:
            success_count += 1
            logger.info(f"✅ {step_name} completed")
        else:
            logger.warning(f"⚠️ {step_name} failed or skipped")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"📊 SETUP SUMMARY: {success_count}/{len(steps)} steps completed")
    
    if success_count == len(steps):
        logger.info("🎉 Database setup completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Start the service: uvicorn app.main:app --reload")
        logger.info("  2. Access API docs: http://localhost:8000/docs")
        logger.info("  3. Test endpoints using Swagger UI")
    else:
        logger.info("⚠️ Some steps failed. Service will run in NO-DB mode.")
        logger.info("")
        logger.info("To retry database setup:")
        logger.info("  1. Fix PostgreSQL connection issues")
        logger.info("  2. Run: python scripts/setup_database.py")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
