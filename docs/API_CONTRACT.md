# API Contract Documentation

## Overview

This document defines the expected API contract between the **Upstream Data Microservice** (Enigma/Financial Data Provider) and this **Fundamental Analysis Microservice**.

## Data Source

The upstream microservice provides financial data for Iranian companies (such as **کاوه - Kaveh**) from the Tehran Stock Exchange (TSE). Data is sourced from CODAL (Comprehensive Database of Listed Companies) through the Enigma platform.

## Sample Data Files (Reference)

The following sample files demonstrate the data structure from the upstream service:

1. **ترازنامه** (Balance Sheet) - `balance-sheet/`
2. **سود و زیان** (Income Statement) - `income-statement/`
3. **نسبت‌های مالی** (Financial Ratios) - `financial-ratios/`
4. **بهای تمام شده** (Cost of Goods Sold) - `cost-of-goods-sold/`
5. **درآمدهای عملیاتی** (Operating Revenue) - `operating-revenue/`
6. **سربار** (Overhead) - `overhead/`
7. **عملکرد ماهانه** (Monthly Performance) - `monthly-performance/`
8. **گردش موجودی** (Inventory Turnover) - `inventory-turnover/`
9. **مواد اولیه** (Raw Materials) - `raw-materials/`
10. **هزینه‌های عمومی** (General Expenses) - `general-expenses/`

---

## API Endpoints

### 1. Company Information

**Endpoint:** `GET /api/v1/companies/{company_id}`

**Response:**
```json
{
  "company_id": "fe7c0931-efd4-4795-852e-91379784f729",
  "ticker": "کاوه",
  "name": "کاوه - شرکت صنایع آهن و فولاد کاوه",
  "sector": "فلزات اساسی",
  "industry": "آهن و فولاد",
  "market": "بورس تهران",
  "currency": "IRR"
}
```

---

### 2. Income Statement (سود و زیان)

**Endpoint:** `GET /api/v1/financial-data/income-statement/{company_id}`

**Query Parameters:**
- `period_type`: `annual` | `quarterly`
- `fiscal_year`: Integer (e.g., 1403)
- `fiscal_quarter`: Integer (1-4) - only for quarterly data

**Response:**
```json
{
  "company_id": "fe7c0931-efd4-4795-852e-91379784f729",
  "period_end_date": "1403-12-29",
  "period_type": "annual",
  "fiscal_year": 1403,
  "fiscal_quarter": null,
  "data": {
    "revenue": 15000000000000,
    "cost_of_revenue": 12000000000000,
    "gross_profit": 3000000000000,
    "operating_expenses": 800000000000,
    "operating_income": 2200000000000,
    "ebitda": 2500000000000,
    "depreciation_amortization": 300000000000,
    "interest_expense": 150000000000,
    "income_before_tax": 2050000000000,
    "income_tax_expense": 410000000000,
    "net_income": 1640000000000,
    "eps_basic": 820,
    "eps_diluted": 810,
    "weighted_avg_shares_basic": 2000000000,
    "weighted_avg_shares_diluted": 2024691358
  }
}
```

**Field Mapping (Persian → English):**
- `درآمد فروش` → `revenue`
- `بهای تمام شده درآمد` → `cost_of_revenue`
- `سود ناخالص` → `gross_profit`
- `هزینه‌های عملیاتی` → `operating_expenses`
- `سود عملیاتی` → `operating_income`
- `سود خالص` → `net_income`

---

### 3. Balance Sheet (ترازنامه)

**Endpoint:** `GET /api/v1/financial-data/balance-sheet/{company_id}`

**Query Parameters:**
- `period_end_date`: Date (YYYY-MM-DD)

**Response:**
```json
{
  "company_id": "fe7c0931-efd4-4795-852e-91379784f729",
  "period_end_date": "1403-12-29",
  "period_type": "annual",
  "fiscal_year": 1403,
  "data": {
    "assets": {
      "total_assets": 25000000000000,
      "current_assets": 10000000000000,
      "cash_and_equivalents": 2000000000000,
      "accounts_receivable": 3000000000000,
      "inventory": 4000000000000,
      "other_current_assets": 1000000000000,
      "non_current_assets": 15000000000000,
      "property_plant_equipment": 12000000000000,
      "intangible_assets": 500000000000,
      "goodwill": 300000000000,
      "long_term_investments": 2200000000000
    },
    "liabilities": {
      "total_liabilities": 12000000000000,
      "current_liabilities": 5000000000000,
      "accounts_payable": 2000000000000,
      "short_term_debt": 1500000000000,
      "other_current_liabilities": 1500000000000,
      "non_current_liabilities": 7000000000000,
      "long_term_debt": 6000000000000,
      "deferred_tax_liabilities": 500000000000,
      "other_non_current_liabilities": 500000000000
    },
    "equity": {
      "total_equity": 13000000000000,
      "common_stock": 5000000000000,
      "retained_earnings": 7000000000000,
      "accumulated_other_comprehensive_income": 1000000000000
    }
  }
}
```

**Field Mapping (Persian → English):**
- `دارایی‌ها` → `assets`
- `دارایی‌های جاری` → `current_assets`
- `موجودی نقد` → `cash_and_equivalents`
- `حساب‌های دریافتنی` → `accounts_receivable`
- `موجودی کالا` → `inventory`
- `بدهی‌ها` → `liabilities`
- `بدهی‌های جاری` → `current_liabilities`
- `حساب‌های پرداختنی` → `accounts_payable`
- `حقوق صاحبان سهام` → `equity`

---

### 4. Cash Flow Statement (صورت جریان وجوه نقد)

**Endpoint:** `GET /api/v1/financial-data/cash-flow/{company_id}`

**Query Parameters:**
- `period_end_date`: Date (YYYY-MM-DD)
- `period_type`: `annual` | `quarterly`

**Response:**
```json
{
  "company_id": "fe7c0931-efd4-4795-852e-91379784f729",
  "period_end_date": "1403-12-29",
  "period_type": "annual",
  "fiscal_year": 1403,
  "data": {
    "operating_activities": {
      "net_income": 1640000000000,
      "depreciation_amortization": 300000000000,
      "change_in_working_capital": -200000000000,
      "change_in_accounts_receivable": -150000000000,
      "change_in_inventory": -100000000000,
      "change_in_accounts_payable": 50000000000,
      "operating_cash_flow": 1740000000000
    },
    "investing_activities": {
      "capital_expenditures": -800000000000,
      "acquisitions": 0,
      "purchase_of_investments": -200000000000,
      "sale_of_investments": 100000000000,
      "investing_cash_flow": -900000000000
    },
    "financing_activities": {
      "dividends_paid": -400000000000,
      "debt_issued": 500000000000,
      "debt_repaid": -300000000000,
      "stock_repurchase": 0,
      "financing_cash_flow": -200000000000
    },
    "net_change_in_cash": 640000000000,
    "beginning_cash_balance": 1360000000000,
    "ending_cash_balance": 2000000000000,
    "free_cash_flow": 940000000000
  }
}
```

---

### 5. Financial Ratios (نسبت‌های مالی)

**Endpoint:** `GET /api/v1/financial-data/ratios/{company_id}`

**Query Parameters:**
- `calculation_date`: Date (YYYY-MM-DD)
- `period_end_date`: Date (YYYY-MM-DD)

**Response:**
```json
{
  "company_id": "fe7c0931-efd4-4795-852e-91379784f729",
  "calculation_date": "1403-12-30",
  "period_end_date": "1403-12-29",
  "ratios": {
    "liquidity": {
      "current_ratio": 2.0,
      "quick_ratio": 1.2,
      "cash_ratio": 0.4,
      "operating_cash_flow_ratio": 0.348,
      "working_capital_ratio": 0.5
    },
    "profitability": {
      "gross_margin": 0.2,
      "operating_margin": 0.1467,
      "net_margin": 0.1093,
      "ebitda_margin": 0.1667,
      "roa": 0.0656,
      "roe": 0.1262,
      "roic": 0.11,
      "roce": 0.12
    },
    "leverage": {
      "debt_to_equity": 0.9231,
      "debt_to_assets": 0.48,
      "equity_multiplier": 1.9231,
      "interest_coverage": 14.67,
      "debt_service_coverage": 2.32,
      "net_debt_to_ebitda": 2.0
    },
    "efficiency": {
      "asset_turnover": 0.6,
      "fixed_asset_turnover": 1.25,
      "inventory_turnover": 3.0,
      "receivables_turnover": 5.0,
      "payables_turnover": 6.0,
      "days_sales_outstanding": 73,
      "days_inventory_outstanding": 122,
      "days_payable_outstanding": 61,
      "cash_conversion_cycle": 134
    },
    "market_value": {
      "pe_ratio": 8.5,
      "pe_ratio_forward": 7.8,
      "peg_ratio": 1.2,
      "pb_ratio": 1.07,
      "ps_ratio": 0.93,
      "pcf_ratio": 8.0,
      "ev_ebitda": 7.2,
      "ev_sales": 1.2,
      "ev_fcf": 19.1,
      "dividend_yield": 0.029,
      "dividend_payout_ratio": 0.244
    },
    "growth": {
      "revenue_growth_yoy": 0.15,
      "revenue_growth_qoq": 0.03,
      "eps_growth_yoy": 0.12,
      "earnings_growth_yoy": 0.12,
      "sustainable_growth_rate": 0.095
    },
    "cash_flow": {
      "operating_cash_flow_margin": 0.116,
      "free_cash_flow_margin": 0.0627,
      "cash_return_on_assets": 0.0696,
      "fcf_to_net_income": 0.573
    }
  }
}
```

---

## Data Requirements

### Data Frequency

- **Balance Sheet**: End of fiscal quarter/year
- **Income Statement**: Quarterly and Annual
- **Cash Flow**: Quarterly and Annual
- **Financial Ratios**: Updated after each financial statement release

### Data Currency

- All monetary values are in **Iranian Rial (IRR)**
- Conversion to USD or other currencies should be done by this microservice using exchange rates

### Date Format

- Persian (Jalali) calendar: `YYYY-MM-DD` (e.g., `1403-12-29`)
- Gregorian calendar conversion handled by this microservice

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "COMPANY_NOT_FOUND",
    "message": "Company with ID 'fe7c0931-efd4-4795-852e-91379784f729' not found",
    "timestamp": "2025-11-13T10:30:00Z"
  }
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Company or data not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Upstream service unavailable

---

## Authentication

**Method:** API Key + OAuth2

```http
GET /api/v1/financial-data/income-statement/{company_id}
Authorization: Bearer {oauth2_token}
X-API-Key: {api_key}
```

---

## Rate Limiting

- **Rate Limit**: 100 requests per minute per API key
- **Burst**: 10 requests per second

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699876800
```

---

## Pagination

For endpoints that return lists (e.g., historical data):

**Request:**
```http
GET /api/v1/financial-data/income-statement/{company_id}/history?page=1&limit=10
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total_pages": 5,
    "total_items": 50
  }
}
```

---

## Data Mapping Examples

### Persian to English Field Names

| Persian | English | Description |
|---------|---------|-------------|
| درآمد فروش | revenue | Total sales revenue |
| بهای تمام شده | cost_of_revenue | Cost of goods sold |
| سود ناخالص | gross_profit | Gross profit |
| سود عملیاتی | operating_income | Operating income |
| سود خالص | net_income | Net income |
| دارایی‌های جاری | current_assets | Current assets |
| بدهی‌های جاری | current_liabilities | Current liabilities |
| حقوق صاحبان سهام | equity | Shareholders' equity |
| جریان نقدی عملیاتی | operating_cash_flow | Operating cash flow |
| نسبت جاری | current_ratio | Current ratio |
| نسبت سریع | quick_ratio | Quick ratio |
| حاشیه سود خالص | net_margin | Net profit margin |

---

## Sample Implementation

### HTTP Client Configuration

```python
import httpx
from typing import Optional

class EnigmaAPIClient:
    """Client for Enigma Financial Data API."""
    
    def __init__(self, base_url: str, api_key: str, oauth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {oauth_token}",
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_income_statement(
        self,
        company_id: str,
        period_type: str = "annual",
        fiscal_year: Optional[int] = None
    ) -> dict:
        """Fetch income statement from upstream API."""
        url = f"{self.base_url}/financial-data/income-statement/{company_id}"
        params = {"period_type": period_type}
        if fiscal_year:
            params["fiscal_year"] = fiscal_year
        
        response = await self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_balance_sheet(self, company_id: str, period_end_date: str) -> dict:
        """Fetch balance sheet from upstream API."""
        url = f"{self.base_url}/financial-data/balance-sheet/{company_id}"
        params = {"period_end_date": period_end_date}
        
        response = await self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
```

---

## Notes

1. **Data Validation**: All incoming data should be validated against Pydantic schemas
2. **Caching**: Consider caching upstream responses (Redis) with TTL based on data type
3. **Retry Logic**: Implement exponential backoff for failed requests
4. **Monitoring**: Track API call success rates, latency, and errors
5. **Persian Support**: Ensure UTF-8 encoding for Persian text
6. **Jalali Calendar**: Use `jdatetime` or `persiantools` for date conversions

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-13 | Initial API contract based on Kaveh sample data |

---

## Contact

For API issues or questions:
- **Email**: api-support@enigma.ir
- **Slack**: #fundamental-analysis-integration
- **Documentation**: https://panel.enigma.ir/docs/api
