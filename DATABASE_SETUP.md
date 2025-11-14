# Database Migration Setup

## Prerequisites

Before running database migrations, ensure:

1. **PostgreSQL 15+ is installed and running**
   ```powershell
   # Check if PostgreSQL is running
   Get-Service postgresql*
   
   # Or start PostgreSQL service
   Start-Service postgresql-x64-15
   ```

2. **Database exists**
   ```powershell
   # Connect to PostgreSQL and create database
   psql -U postgres
   CREATE DATABASE fundamental_analysis;
   \q
   ```

3. **Environment variables are set** (in `.env` file)
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fundamental_analysis
   SECRET_KEY=your-secret-key-here
   ```

## Running Migrations

### 1. Generate Initial Migration

The migration has already been configured in `alembic/env.py` and `alembic.ini`. When database is ready:

```powershell
# From project root directory
E:/Shakour/GravityProjects/GravityFundamentalAnalysis/Gravity_FundamentalAnalysis/.venv/Scripts/python.exe -m alembic revision --autogenerate -m "Initial schema"
```

This will create a migration file in `alembic/versions/` with all the database tables:
- `companies`
- `income_statements`
- `balance_sheets`
- `cash_flow_statements`
- `financial_ratios`
- `valuations`
- `risk_assessments`
- `market_data`

### 2. Apply Migration

```powershell
E:/Shakour/GravityProjects/GravityFundamentalAnalysis/Gravity_FundamentalAnalysis/.venv/Scripts/python.exe -m alembic upgrade head
```

### 3. Check Migration Status

```powershell
E:/Shakour/GravityProjects/GravityFundamentalAnalysis/Gravity_FundamentalAnalysis/.venv/Scripts/python.exe -m alembic current
```

### 4. Rollback Migration (if needed)

```powershell
# Rollback one version
E:/Shakour/GravityProjects/GravityFundamentalAnalysis/Gravity_FundamentalAnalysis/.venv/Scripts/python.exe -m alembic downgrade -1

# Rollback to base
E:/Shakour/GravityProjects/GravityFundamentalAnalysis/Gravity_FundamentalAnalysis/.venv/Scripts/python.exe -m alembic downgrade base
```

## Database Schema

The migration will create the following schema:

### Core Tables

1. **companies** - Company master data
   - Ticker, name, sector, industry
   - Market cap, exchange, currency
   - Multi-tenant support (tenant_id)

2. **income_statements** - Income statement data
   - Revenue, expenses, net income
   - EBITDA, EPS (basic/diluted)
   - Annual & quarterly periods

3. **balance_sheets** - Balance sheet data
   - Assets (current & non-current)
   - Liabilities (current & non-current)
   - Equity components

4. **cash_flow_statements** - Cash flow data
   - Operating, investing, financing activities
   - Free cash flow calculation

5. **financial_ratios** - 50+ calculated ratios
   - Liquidity, profitability, leverage
   - Efficiency, market value, growth
   - Cash flow ratios

6. **valuations** - Valuation results
   - DCF, Comparables, Asset-Based methods
   - Fair value, enterprise value
   - Assumptions and sensitivity analysis (JSONB)

7. **risk_assessments** - Risk analysis
   - Business, financial, operational risks
   - Altman Z-Score, credit rating
   - Beta, volatility, VaR

8. **market_data** - Daily price & volume
   - OHLC prices, adjusted close
   - Volume, market cap

### Key Features

- **UUID primary keys** for all tables
- **Timestamps** (created_at, updated_at) on all records
- **Multi-tenancy** via tenant_id column
- **Foreign key constraints** with CASCADE delete
- **Indexes** on frequently queried columns (company_id, dates, ticker)
- **NUMERIC precision** for financial data (no floating-point errors)
- **JSONB columns** for flexible JSON storage (parameters, assumptions)

## Troubleshooting

### Connection Refused Error

If you see "Connection refused" error:
1. Check PostgreSQL is running: `Get-Service postgresql*`
2. Verify connection details in `.env`
3. Test connection: `psql -U postgres -d fundamental_analysis`

### Module Not Found Errors

If you see import errors:
```powershell
# Install missing packages
pip install alembic asyncpg sqlalchemy psycopg2-binary
```

### Async/Sync Driver Issues

Alembic uses synchronous connections (psycopg2), while the app uses async (asyncpg). This is by design:
- **Migrations**: postgresql:// (psycopg2) - synchronous
- **Runtime app**: postgresql+asyncpg:// (asyncpg) - asynchronous

The `alembic/env.py` automatically converts DATABASE_URL from asyncpg to psycopg2 format.

## Next Steps

After migrations are applied:

1. **Verify tables exist**
   ```sql
   \c fundamental_analysis
   \dt
   \d companies
   ```

2. **Start the FastAPI application**
   ```powershell
   uvicorn app.main:app --reload
   ```

3. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. **Run tests**
   ```powershell
   pytest -v
   ```
