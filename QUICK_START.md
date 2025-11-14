# Quick Start Guide - Gravity Fundamental Analysis

## 🚀 5-Minute Setup

### 1. Install Test Dependencies
```powershell
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite
```

### 2. Run Tests (No Database Required)
```powershell
# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test
pytest tests/test_company_service.py -v

# Run unit tests only
pytest -m unit
```

### 3. Start with Docker (Recommended)
```powershell
# Start all services (PostgreSQL, Redis, Kafka, App)
docker-compose -f docker/docker-compose.yml up -d

# Check logs
docker-compose -f docker/docker-compose.yml logs -f app

# Access API
# Swagger UI: http://localhost:8000/api/v1/docs
```

## 🗄️ Database Setup (Without Docker)

### Step 1: Install PostgreSQL
```powershell
# Check if PostgreSQL is installed
Get-Service postgresql*

# If not installed, download from: https://www.postgresql.org/download/windows/
```

### Step 2: Start PostgreSQL Service
```powershell
Start-Service postgresql-x64-15
```

### Step 3: Create Database
```powershell
# Connect to PostgreSQL
psql -U postgres

# In psql prompt:
CREATE DATABASE fundamental_analysis;
\q
```

### Step 4: Run Migrations
```powershell
# From project root
python -m alembic upgrade head
```

### Step 5: Start Application
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📝 Common Commands

### Development
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic pydantic-settings

# Run with hot reload
uvicorn app.main:app --reload

# Format code
black app tests
isort app tests

# Type checking
mypy app

# Linting
flake8 app tests
```

### Database
```powershell
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Check current version
alembic current
```

### Testing
```powershell
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_company_service.py

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x

# Run tests matching pattern
pytest -k "test_create"
```

### Docker
```powershell
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Start specific service
docker-compose -f docker/docker-compose.yml up -d postgres

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop all services
docker-compose -f docker/docker-compose.yml down

# Rebuild and start
docker-compose -f docker/docker-compose.yml up -d --build

# Remove volumes (clean slate)
docker-compose -f docker/docker-compose.yml down -v
```

## 🧪 Testing the API

### Using Swagger UI
1. Open http://localhost:8000/api/v1/docs
2. Click "Authorize" button
3. Enter Bearer token (get from login endpoint)
4. Try out the endpoints

### Using curl
```bash
# Health check
curl http://localhost:8000/health

# Create company (requires authentication)
curl -X POST http://localhost:8000/api/v1/companies/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "market_cap": 3000000000000.0,
    "country": "USA",
    "currency": "USD",
    "exchange": "NASDAQ"
  }'

# List companies
curl -X GET "http://localhost:8000/api/v1/companies/?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search companies
curl -X GET "http://localhost:8000/api/v1/companies/search?q=Apple" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Using Python requests
```python
import requests

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Get token (mock - implement actual authentication)
token = "your-jwt-token-here"
headers = {"Authorization": f"Bearer {token}"}

# Create company
response = requests.post(
    f"{BASE_URL}/companies/",
    headers=headers,
    json={
        "ticker": "GOOGL",
        "name": "Alphabet Inc.",
        "sector": "Technology",
        "industry": "Internet Services",
    }
)
print(response.json())

# Get company
company_id = response.json()["id"]
response = requests.get(f"{BASE_URL}/companies/{company_id}", headers=headers)
print(response.json())
```

## 🔍 Troubleshooting

### "ModuleNotFoundError: No module named 'X'"
```powershell
# Install missing packages
pip install X

# Or install all dependencies
pip install -r requirements.txt
```

### "Connection refused" (PostgreSQL)
```powershell
# Check if PostgreSQL is running
Get-Service postgresql*

# Start PostgreSQL
Start-Service postgresql-x64-15

# Check connection
psql -U postgres -d fundamental_analysis
```

### "Alembic can't find models"
```powershell
# Make sure you're in the project root directory
cd E:\Shakour\GravityProjects\GravityFundamentalAnalysis\Gravity_FundamentalAnalysis

# Run migration
python -m alembic upgrade head
```

### Tests failing
```powershell
# Run with verbose output to see details
pytest -v

# Run single test to isolate issue
pytest tests/test_company_service.py::test_create_company -v

# Clear pytest cache
pytest --cache-clear
```

## 📊 Monitoring & Observability

### Prometheus Metrics
```powershell
# Access Prometheus
Start-Process "http://localhost:9090"

# View metrics endpoint
curl http://localhost:8000/metrics
```

### Grafana Dashboards
```powershell
# Access Grafana
Start-Process "http://localhost:3001"

# Default credentials:
# Username: admin
# Password: admin
```

### Logs
```powershell
# View application logs
docker-compose -f docker/docker-compose.yml logs -f app

# View PostgreSQL logs
docker-compose -f docker/docker-compose.yml logs -f postgres

# View Redis logs
docker-compose -f docker/docker-compose.yml logs -f redis
```

## 🎯 Next Steps

1. **Complete Test Coverage**
   - Add integration tests for endpoints
   - Add tests for financial statements service
   - Target: >95% coverage

2. **Implement Ratio Calculation Service**
   - 50+ financial ratios
   - Automatic calculation on new statements
   - Historical ratio tracking

3. **Add Valuation Endpoints**
   - DCF valuation
   - Comparables analysis
   - Asset-based valuation

4. **Deploy to Production**
   - Kubernetes deployment
   - CI/CD pipeline
   - Monitoring & alerting

## 📚 Additional Resources

- **Full Documentation**: See `README.md`
- **API Specification**: See `requirements.md`
- **Project Roadmap**: See `TODO.md`
- **Team Structure**: See `TEAM_PROMPT.md`
- **Database Guide**: See `DATABASE_SETUP.md`
- **Progress Report**: See `PROGRESS_REPORT.md`

## 💡 Tips

- Always activate virtual environment before running commands
- Use `--reload` flag with uvicorn for development
- Run tests before committing code
- Check test coverage regularly: `pytest --cov=app`
- Use Docker Compose for consistent development environment
- Keep `.env` file secure (never commit to Git)
- Use Swagger UI for interactive API testing
- Monitor logs for debugging issues

## 🆘 Need Help?

- Check existing tests for examples
- Review service layer implementations
- Consult FastAPI documentation: https://fastapi.tiangolo.com/
- Check SQLAlchemy async docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Review Alembic migration guide: https://alembic.sqlalchemy.org/
