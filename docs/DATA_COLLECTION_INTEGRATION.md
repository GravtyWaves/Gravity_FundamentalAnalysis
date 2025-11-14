# Data Collection Integration

این سند نحوه ارتباط میکروسرویس Fundamental Analysis با میکروسرویس Data Collection را توضیح می‌دهد.

## معماری

```
┌─────────────────────────┐          ┌──────────────────────────┐
│ Data Collection Service │  ◄────►  │ Fundamental Analysis     │
│ (Port 8001)             │          │ (Port 8000)              │
│                         │          │                          │
│ - Fetch data from APIs  │          │ - Store financial data   │
│ - Clean & validate data │          │ - Calculate ratios       │
│ - Transform data        │          │ - Perform valuations     │
└─────────────────────────┘          └──────────────────────────┘
```

## تنظیمات اولیه

### 1. تنظیم Environment Variables

در فایل `.env` خود:

```bash
# Data Collection Microservice
DATA_COLLECTION_SERVICE_URL=http://localhost:8001
DATA_COLLECTION_API_KEY=your-api-key-here
DATA_COLLECTION_TIMEOUT=30.0
```

### 2. راه‌اندازی Data Collection Service

اطمینان حاصل کنید که میکروسرویس Data Collection روی پورت 8001 در حال اجرا است.

## استفاده از API Endpoints

### 1. بررسی سلامت Data Collection Service

```bash
GET /api/v1/data-collection/health
```

**Response:**
```json
{
  "service": "data-collection",
  "status": "healthy",
  "timestamp": "2024-01-15"
}
```

### 2. دریافت لیست Ticker های پشتیبانی شده

```bash
GET /api/v1/data-collection/tickers
```

**Response:**
```json
["AAPL", "MSFT", "GOOGL", "TSLA", ...]
```

### 3. بررسی وضعیت داده برای یک Ticker

```bash
GET /api/v1/data-collection/status/{ticker}
```

**Response:**
```json
{
  "ticker": "AAPL",
  "available": true,
  "last_update": "2024-01-15T10:30:00",
  "data_types": ["income_statement", "balance_sheet", "cash_flow", "market_data"]
}
```

### 4. دریافت Income Statement

```bash
GET /api/v1/data-collection/income-statement/{ticker}
  ?period_type=annual
  &start_date=2020-01-01
  &end_date=2024-01-01
```

**Response:**
```json
{
  "ticker": "AAPL",
  "period_type": "annual",
  "data_type": "income_statement",
  "records": [
    {
      "fiscal_year": 2023,
      "revenue": 383285000000,
      "gross_profit": 169148000000,
      "operating_income": 114301000000,
      "net_income": 96995000000,
      ...
    }
  ],
  "count": 4
}
```

### 5. دریافت Balance Sheet

```bash
GET /api/v1/data-collection/balance-sheet/{ticker}
  ?period_type=annual
```

### 6. دریافت Cash Flow Statement

```bash
GET /api/v1/data-collection/cash-flow/{ticker}
  ?period_type=annual
```

### 7. دریافت Market Data

```bash
GET /api/v1/data-collection/market-data/{ticker}
  ?start_date=2023-01-01
  &end_date=2024-01-01
```

### 8. دریافت اطلاعات Company

```bash
GET /api/v1/data-collection/company-info/{ticker}
```

**Response:**
```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": 3000000000000,
  "country": "USA",
  "currency": "USD",
  "exchange": "NASDAQ",
  "employees": 164000,
  "fiscal_year_end": "09-30"
}
```

### 9. دریافت همه Financial Statements یکجا

```bash
GET /api/v1/data-collection/financial-statements/{ticker}
  ?period_type=annual
```

**Response:**
```json
{
  "ticker": "AAPL",
  "period_type": "annual",
  "data": {
    "income_statements": [...],
    "balance_sheets": [...],
    "cash_flow_statements": [...]
  }
}
```

### 10. درخواست Refresh داده

```bash
POST /api/v1/data-collection/refresh/{ticker}
```

**Response:**
```json
{
  "ticker": "AAPL",
  "status": "refresh_requested",
  "details": {
    "job_id": "abc123",
    "estimated_completion": "2024-01-15T11:00:00"
  }
}
```

## Data Sync Endpoints

این endpoint ها داده را از Data Collection دریافت کرده و در دیتابیس محلی ذخیره می‌کنند.

### 1. Sync کردن اطلاعات Company

```bash
POST /api/v1/data-collection/sync/company/{ticker}
Headers:
  X-Tenant-ID: tenant123
```

**Response:**
```json
{
  "status": "success",
  "message": "Company AAPL synced successfully",
  "company": {
    "id": 1,
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "sector": "Technology",
    "industry": "Consumer Electronics"
  }
}
```

### 2. Sync کردن تمام Financial Statements

```bash
POST /api/v1/data-collection/sync/financial-statements/{ticker}
  ?period_type=annual
  &start_date=2020-01-01
  &end_date=2024-01-01
Headers:
  X-Tenant-ID: tenant123
```

**Response:**
```json
{
  "status": "success",
  "message": "Financial data for AAPL synced successfully",
  "company_id": 1,
  "company_name": "Apple Inc.",
  "records_synced": {
    "income_statements": 4,
    "balance_sheets": 4,
    "cash_flow_statements": 4,
    "total": 12
  }
}
```

### 3. Sync کردن فقط Income Statements

```bash
POST /api/v1/data-collection/sync/income-statements/{ticker}
  ?period_type=annual
Headers:
  X-Tenant-ID: tenant123
```

## استفاده از Python Client

### مثال 1: استفاده مستقیم از Client

```python
from app.services.data_collection_client import DataCollectionClient

# Initialize client
client = DataCollectionClient()

# Check health
is_healthy = await client.health_check()

# Fetch income statements
income_data = await client.fetch_income_statement(
    ticker="AAPL",
    period_type="annual",
    start_date=date(2020, 1, 1),
    end_date=date(2024, 1, 1)
)

# Fetch all financial data
all_data = await client.fetch_all_financial_data(
    ticker="AAPL",
    period_type="annual"
)
```

### مثال 2: استفاده از Integration Service

```python
from app.services.data_integration_service import DataIntegrationService

# Initialize service
integration_service = DataIntegrationService(db, tenant_id="tenant123")

# Sync company
company = await integration_service.sync_company_data("AAPL")

# Sync all financial data
result = await integration_service.sync_all_financial_data(
    ticker="AAPL",
    period_type="annual",
    start_date=date(2020, 1, 1),
    end_date=date(2024, 1, 1)
)

print(f"Synced {result['total_records']} records")
```

## Error Handling

### DataCollectionError

زمانی رخ می‌دهد که سرویس Data Collection در دسترس نباشد یا خطا برگرداند:

```python
try:
    data = await client.fetch_income_statement("AAPL")
except DataCollectionError as e:
    # Handle connection or API errors
    logger.error(f"Data collection failed: {e}")
```

### DataIntegrationError

زمانی رخ می‌دهد که sync کردن داده به دیتابیس محلی با خطا مواجه شود:

```python
try:
    result = await integration_service.sync_all_financial_data("AAPL")
except DataIntegrationError as e:
    # Handle integration errors
    logger.error(f"Data integration failed: {e}")
```

## Workflow توصیه شده

### Workflow 1: اضافه کردن یک Company جدید

```bash
# Step 1: Check if ticker is supported
GET /api/v1/data-collection/status/AAPL

# Step 2: Sync company info
POST /api/v1/data-collection/sync/company/AAPL

# Step 3: Sync all financial statements
POST /api/v1/data-collection/sync/financial-statements/AAPL?period_type=annual

# Step 4: Calculate ratios
POST /api/v1/ratios/calculate
{
  "company_id": 1,
  "fiscal_year": 2023,
  "period_type": "annual"
}

# Step 5: Perform valuation
POST /api/v1/valuations/dcf
{
  "company_id": 1,
  ...
}
```

### Workflow 2: به‌روزرسانی داده موجود

```bash
# Step 1: Request refresh from data collection
POST /api/v1/data-collection/refresh/AAPL

# Step 2: Wait for refresh completion (check status)
GET /api/v1/data-collection/status/AAPL

# Step 3: Sync updated data
POST /api/v1/data-collection/sync/financial-statements/AAPL

# Step 4: Recalculate ratios and valuations
...
```

## تنظیمات پیشرفته

### Custom Timeout

```python
client = DataCollectionClient(timeout=60.0)  # 60 seconds
```

### Custom Base URL

```python
client = DataCollectionClient(base_url="https://data-collection.example.com")
```

### با API Key

در فایل `.env`:
```
DATA_COLLECTION_API_KEY=your-api-key
```

Client به صورت خودکار از تنظیمات استفاده می‌کند.

## نکات مهم

1. **Multi-Tenancy**: همیشه header `X-Tenant-ID` را در sync endpoint ها ارسال کنید
2. **Duplicate Prevention**: Integration service به صورت خودکار از duplicate شدن داده جلوگیری می‌کند
3. **Error Handling**: همیشه `DataCollectionError` و `DataIntegrationError` را handle کنید
4. **Rate Limiting**: Data Collection Service ممکن است rate limit داشته باشد
5. **Timeout**: برای داده‌های تاریخی طولانی، timeout را افزایش دهید

## مثال کامل: Full Integration

```python
async def integrate_company_full(ticker: str, db: AsyncSession, tenant_id: str):
    """Complete integration workflow for a new company."""
    
    # Initialize services
    data_client = DataCollectionClient()
    integration_service = DataIntegrationService(db, tenant_id, data_client)
    
    try:
        # 1. Check availability
        logger.info(f"Checking data availability for {ticker}")
        status = await data_client.check_data_availability(ticker)
        
        if not status.get("available"):
            logger.error(f"Data not available for {ticker}")
            return None
        
        # 2. Sync all data
        logger.info(f"Starting full sync for {ticker}")
        result = await integration_service.sync_all_financial_data(
            ticker=ticker,
            period_type="annual",
            start_date=date(2019, 1, 1),
            end_date=date.today()
        )
        
        logger.info(f"Sync completed: {result['total_records']} records")
        
        # 3. Calculate ratios for latest year
        # ... ratio calculation logic
        
        # 4. Perform valuation
        # ... valuation logic
        
        return result
        
    except (DataCollectionError, DataIntegrationError) as e:
        logger.error(f"Integration failed for {ticker}: {e}")
        raise
```

## مستندات API کامل

برای مشاهده API documentation کامل:

```bash
# Start the service
uvicorn app.main:app --reload

# Open Swagger UI
http://localhost:8000/docs

# Open ReDoc
http://localhost:8000/redoc
```

## پشتیبانی

در صورت بروز مشکل، لاگ‌ها را بررسی کنید:

```bash
# Check logs for errors
LOG_LEVEL=DEBUG uvicorn app.main:app
```
