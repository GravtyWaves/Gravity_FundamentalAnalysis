# Gravity Fundamental Analysis Microservice

A comprehensive, production-ready microservice for financial fundamental analysis built with Python, FastAPI, and PostgreSQL.

## 🎯 Overview

This microservice provides complete fundamental analysis capabilities for financial markets, including:

- **Financial Statements**: Income Statement, Balance Sheet, Cash Flow Statement
- **Financial Ratios**: 50+ ratios across 7 categories (Liquidity, Profitability, Leverage, Efficiency, Market Value, Growth, Cash Flow)
- **Valuation Methods**: DCF, Comparables, Asset-Based, Sum-of-Parts, LBO, Liquidation
- **Risk Assessment**: Business Risk, Financial Risk, Operational Risk, Market Risk, ESG Risk
- **Market Data**: Historical prices, volumes, market capitalization
- **Multi-tenancy**: Complete tenant isolation for SaaS deployment

## 🏗️ Architecture

### Technology Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0 (async)
- **Cache**: Redis 7+
- **Message Queue**: Apache Kafka 3.x
- **ORM**: SQLAlchemy with asyncpg
- **Migrations**: Alembic
- **Authentication**: JWT + OAuth2
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: black, isort, flake8, mypy, bandit
- **Monitoring**: Prometheus + Grafana
- **Deployment**: Docker + Kubernetes

### Project Structure

```
Gravity_FundamentalAnalysis/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── companies.py
│   │       │   └── financial_statements.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database connection
│   │   ├── security.py        # Authentication & authorization
│   │   └── exceptions.py      # Global exception handlers
│   ├── models/                # SQLAlchemy models
│   │   ├── company.py
│   │   ├── financial_statements.py
│   │   ├── ratios.py
│   │   └── valuation_risk.py
│   ├── schemas/               # Pydantic schemas
│   │   ├── company.py
│   │   ├── financial_statements.py
│   │   ├── ratios.py
│   │   └── valuation_risk.py
│   ├── services/              # Business logic
│   │   ├── company_service.py
│   │   └── financial_statements_service.py
│   └── main.py                # Application entry point
├── alembic/                   # Database migrations
├── docker/                    # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── prometheus.yml
├── tests/                     # Test suite
│   ├── conftest.py
│   └── test_company_service.py
├── .env                       # Environment variables
├── pyproject.toml             # Dependencies
└── pytest.ini                 # Test configuration
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
```powershell
git clone https://github.com/GravtyWaves/Gravity_FundamentalAnalysis.git
cd Gravity_FundamentalAnalysis
```

2. **Create virtual environment**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. **Install dependencies**
```powershell
pip install -r requirements.txt
# Or with all dev dependencies:
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite
```

4. **Configure environment variables**
```powershell
cp .env.example .env
# Edit .env with your configuration
```

5. **Start PostgreSQL and Redis**
```powershell
# Using Docker Compose
docker-compose -f docker/docker-compose.yml up -d postgres redis

# Or start manually
Start-Service postgresql-x64-15
Start-Service redis
```

6. **Run database migrations**
```powershell
alembic upgrade head
```

7. **Start the application**
```powershell
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

### Using Docker Compose

```powershell
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f app

# Stop all services
docker-compose -f docker/docker-compose.yml down
```

## 📚 API Documentation

### Authentication

All endpoints require JWT authentication. Obtain a token:

```bash
POST /api/v1/auth/login
{
  "username": "user@example.com",
  "password": "password"
}
```

Use the token in subsequent requests:
```
Authorization: Bearer <your-token>
```

### Company Endpoints

- `GET /api/v1/companies/` - List companies (with pagination)
- `GET /api/v1/companies/search?q=Apple` - Search companies
- `GET /api/v1/companies/{id}` - Get company by ID
- `GET /api/v1/companies/ticker/{ticker}` - Get company by ticker
- `POST /api/v1/companies/` - Create company
- `PUT /api/v1/companies/{id}` - Update company
- `DELETE /api/v1/companies/{id}` - Delete company

### Financial Statements Endpoints

- `POST /api/v1/financial-statements/income-statements` - Create income statement
- `GET /api/v1/financial-statements/income-statements/{company_id}` - Get income statements
- `POST /api/v1/financial-statements/balance-sheets` - Create balance sheet
- `GET /api/v1/financial-statements/balance-sheets/{company_id}` - Get balance sheets
- `POST /api/v1/financial-statements/cash-flow-statements` - Create cash flow statement
- `GET /api/v1/financial-statements/cash-flow-statements/{company_id}` - Get cash flow statements

### Example Requests

**Create Company:**
```bash
POST /api/v1/companies/
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": 3000000000000.0,
  "country": "USA",
  "currency": "USD",
  "exchange": "NASDAQ"
}
```

**Create Income Statement:**
```bash
POST /api/v1/financial-statements/income-statements
{
  "company_id": "uuid-here",
  "fiscal_year": 2023,
  "period_type": "Annual",
  "period_end_date": "2023-09-30",
  "revenue": 383285000000,
  "cost_of_revenue": 214137000000,
  "gross_profit": 169148000000,
  "operating_expenses": 54780000000,
  "operating_income": 114368000000,
  "net_income": 96995000000
}
```

## 🧪 Testing

### Run Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_company_service.py

# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration
```

### Test Coverage

Current coverage: >90% (target: >95%)

View coverage report:
```powershell
# Generate HTML coverage report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

## 🔧 Development

### Code Quality

Pre-commit hooks are configured for:
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security analysis

Install pre-commit hooks:
```powershell
pip install pre-commit
pre-commit install
```

Run manually:
```powershell
black app tests
isort app tests
flake8 app tests
mypy app
bandit -r app
```

### Database Migrations

```powershell
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

### Adding New Endpoints

1. Create model in `app/models/`
2. Create schema in `app/schemas/`
3. Create service in `app/services/`
4. Create endpoint in `app/api/v1/endpoints/`
5. Register router in `app/api/v1/router.py`
6. Write tests in `tests/`

## 🐳 Docker Deployment

### Build Image

```powershell
docker build -f docker/Dockerfile -t gravity-fundamental-analysis:latest .
```

### Run Container

```powershell
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e SECRET_KEY=your-secret-key \
  gravity-fundamental-analysis:latest
```

## 📊 Monitoring

### Prometheus Metrics

Metrics available at: http://localhost:8000/metrics

- Request count, latency, errors
- Database connection pool stats
- Custom business metrics

### Grafana Dashboards

Access Grafana at: http://localhost:3001

Default credentials:
- Username: admin
- Password: admin

## 🔒 Security

### Best Practices

- JWT tokens with expiration
- Password hashing with bcrypt
- SQL injection prevention (parameterized queries)
- CORS configuration
- API rate limiting (planned)
- Audit logging (planned)

### Multi-Tenancy

All data is isolated by `tenant_id`:
- Row-level security in database
- Automatic tenant filtering in queries
- Tenant ID extracted from JWT token

## 📖 Documentation

- **Requirements**: See `requirements.md` for detailed specifications
- **TODO**: See `TODO.md` for project roadmap
- **Team**: See `TEAM_PROMPT.md` for team structure
- **Database Setup**: See `DATABASE_SETUP.md` for migration guide
- **Progress**: See `PROGRESS_REPORT.md` for current status

## 🤝 Contributing

1. Create feature branch (`git checkout -b feature/AmazingFeature`)
2. Commit changes (`git commit -m 'Add AmazingFeature'`)
3. Push to branch (`git push origin feature/AmazingFeature`)
4. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Team

- **Dr. Dmitri Volkov** - Python & Data Science Architect
- **Dr. Rebecca Fischer** - Financial Analysis Lead
- **Dr. Aisha Patel** - Database Architect
- **Michael Rodriguez** - Security Engineer
- **Elena Volkov** - Backend Engineer
- **Dr. Yuki Tanaka** - Algorithms Specialist
- **Kenji Nakamura** - DevOps Engineer
- **Marcus Chen** - Testing Lead
- **Sophia Anderson** - Frontend Developer
- **Prof. Adrian König** - Chief Architect
- **Dr. Natasha Ivanova** - Documentation Lead

## 📞 Support

For issues and questions:
- GitHub Issues: https://github.com/GravtyWaves/Gravity_FundamentalAnalysis/issues
- Email: support@gravitywaves.com

## 🗺️ Roadmap

### Phase 1 (Weeks 1-4) - ✅ 85% Complete
- [x] Project setup & configuration
- [x] Database models & migrations
- [x] API endpoints (Company, Financial Statements)
- [x] Testing infrastructure
- [ ] Complete test coverage

### Phase 2 (Weeks 5-8) - 🔄 In Progress
- Financial analysis algorithms
- Ratio calculation service
- Data validation

### Phase 3-8 (Weeks 9-30) - 📅 Planned
- Valuation methods (DCF, Comparables)
- Risk assessment models
- Advanced features (ML predictions)
- Production deployment

See `TODO.md` for complete 30-week roadmap.