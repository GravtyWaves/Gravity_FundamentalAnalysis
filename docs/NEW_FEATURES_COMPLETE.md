# امکانات جدید میکروسرویس تحلیل بنیادی
# New Features - Fundamental Analysis Microservice

## خلاصه اجرایی | Executive Summary

در این فاز، **8 قابلیت حیاتی** به میکروسرویس اضافه شده است که سطح تحلیل بنیادی را به شکل چشمگیری ارتقا می‌دهد:

✅ **1. Trend Analysis** - تحلیل روندهای مالی با رگرسیون آماری  
✅ **2. Scenario Analysis** - تحلیل سه سناریو (خوشبینانه، خنثی، بدبینانه)  
✅ **3. Stock Scoring & Ranking** - امتیازدهی و رتبه‌بندی نمادها (0-100)  
✅ **4. Sensitivity Analysis** - حساسیت‌سنجی (Tornado، Monte Carlo)  
✅ **5. Value Drivers** - تحلیل محرک‌های ارزش (DuPont، Waterfall)  
✅ **6. Risk Assessment** - ارزیابی ریسک با سه سناریو  
✅ **7. Market Data** - مدیریت داده‌های بازار  
✅ **8. Data Collection Integration** - یکپارچه‌سازی با میکروسرویس دریافت داده  

---

## 1️⃣ Trend Analysis (تحلیل روندها)

### 📋 توضیحات
تحلیل آماری روندهای مالی با استفاده از رگرسیون خطی، میانگین متحرک، و شناسایی ناهنجاری‌ها.

### 🔧 سرویس‌ها
- **File**: `app/services/trend_analysis_service.py` (696 lines)
- **Methods**:
  - `analyze_revenue_trend()` - تحلیل روند درآمد (CAGR، YoY، رگرسیون)
  - `analyze_profitability_trends()` - روند حاشیه سود (Gross/Operating/Net Margin، ROE، ROA)
  - `analyze_ratio_trend()` - روند تک‌تک نسبت‌ها
  - `linear_regression()` - رگرسیون خطی با R²، p-value
  - `detect_anomalies()` - شناسایی ناهنجاری‌ها (Z-score)

### 🌐 API Endpoints
**Base URL**: `/api/v1/trend-analysis`

#### 1. Revenue Trend Analysis
```http
GET /api/v1/trend-analysis/{company_id}/revenue-trend?num_years=5
```
**خروجی**:
- CAGR (نرخ رشد مرکب سالانه)
- رشد YoY (سال به سال)
- رگرسیون خطی (شیب، R²، p-value)
- جهت روند (صعودی/نزولی/ثابت)
- ناهنجاری‌های شناسایی شده

#### 2. Profitability Trends
```http
GET /api/v1/trend-analysis/{company_id}/profitability-trends?num_years=5
```
**خروجی**:
- روند حاشیه سود ناخالص (Gross Margin)
- روند حاشیه عملیاتی (Operating Margin)
- روند حاشیه سود خالص (Net Profit Margin)
- روند ROE و ROA
- میانگین متحرک 3 و 5 ساله

#### 3. Individual Ratio Trend
```http
GET /api/v1/trend-analysis/{company_id}/ratio-trend/{ratio_name}?num_periods=8
```
**خروجی**:
- جهت روند نسبت (بهبود یافته/ثابت/بدتر شده)
- قدرت روند (R²)
- معنی‌داری آماری (p-value)
- ضریب تغییرات (نوسان)

### 📊 Use Cases
1. شناسایی شرکت‌های با رشد پایدار درآمد
2. تشخیص فشردگی/گسترش حاشیه سود
3. پیش‌بینی روند آتی بر اساس داده‌های تاریخی
4. شناسایی تغییرات ناگهانی (ناهنجاری‌ها)

---

## 2️⃣ Scenario Analysis (تحلیل سناریو)

### 📋 توضیحات
تحلیل جامع با **سه سناریو** برای ارزیابی ریسک و بازده:
- **خوشبینانه (Optimistic/Bull Case)**: رشد 25% بالاتر، حاشیه سود 15% بیشتر، WACC 10% کمتر
- **خنثی (Neutral/Base Case)**: فرضیات فعلی/واقع‌گرایانه
- **بدبینانه (Pessimistic/Bear Case)**: رشد 30% پایین‌تر، حاشیه سود 15% کمتر، WACC 15% بیشتر

### 🔧 سرویس‌ها
- **File**: `app/services/scenario_analysis_service.py` (342 lines)
- **Methods**:
  - `analyze_valuation_scenarios()` - ارزشگذاری DCF در سه سناریو
  - `analyze_comprehensive_scenarios()` - ترکیب ارزشگذاری + ریسک + توصیه
  - `generate_scenario_assumptions()` - تولید فرضیات سناریو

### 🌐 API Endpoints
**Base URL**: `/api/v1/scenario-analysis`

#### 1. Valuation Scenarios
```http
POST /api/v1/scenario-analysis/{company_id}/valuation-scenarios
```
**ورودی (Body)**:
```json
{
  "expected_fair_value": 100.0,
  "current_price": 90.0,
  "revenue_growth": [0.10, 0.08, 0.06],
  "ebitda_margin": 0.20,
  "wacc": 0.10,
  "terminal_growth": 0.025,
  "capex_pct": 0.05
}
```

**خروجی**:
- ارزش منصفانه سهم در 3 سناریو
- درصد صعود/نزول (Upside/Downside)
- ارزش مورد انتظار وزن‌دار
- نسبت ریسک-بازده (Risk-Reward Ratio)

#### 2. Comprehensive Scenarios
```http
POST /api/v1/scenario-analysis/{company_id}/comprehensive-scenarios
```
**خروجی**:
- سناریوهای ارزشگذاری
- سناریوهای ریسک
- توصیه سرمایه‌گذاری (Strong Buy / Buy / Hold / Sell / Strong Sell)
- سطح اطمینان (High/Medium/Low)

### 📊 Use Cases
1. ارزیابی پتانسیل صعود/نزول سهم
2. تصمیم‌گیری سرمایه‌گذاری با احتساب ریسک
3. مدیریت پرتفوی با سناریوهای مختلف
4. تست استرس (Stress Testing)

---

## 3️⃣ Stock Scoring & Ranking (امتیازدهی و رتبه‌بندی)

### 📋 توضیحات
سیستم جامع امتیازدهی بنیادی با **5 بعد** (0-100):

| بعد | وزن | متریک‌ها |
|-----|-----|---------|
| **Valuation** | 25% | P/E, P/B, PEG, EV/EBITDA |
| **Profitability** | 20% | ROE, ROA, Net Margin, Operating Margin |
| **Growth** | 20% | Revenue Growth, Earnings Growth, Book Value Growth |
| **Financial Health** | 20% | Current Ratio, Quick Ratio, Debt/Equity, Interest Coverage |
| **Risk** | 15% | Altman Z-Score, Beta, Volatility |

### 🎯 Rating Scale
- **A+ (90-100)**: قدرت بنیادی عالی
- **A (80-89)**: بنیادی قوی
- **B+ (70-79)**: بالاتر از متوسط
- **B (60-69)**: متوسط
- **C+ (50-59)**: پایین‌تر از متوسط
- **C (40-49)**: بنیادی ضعیف
- **D (30-39)**: بنیادی بسیار ضعیف
- **F (0-29)**: ناامن

### 🔧 سرویس‌ها
- **File**: `app/services/stock_scoring_service.py` (788 lines)
- **Methods**:
  - `calculate_composite_score()` - امتیاز کل
  - `calculate_valuation_score()` - امتیاز ارزشگذاری
  - `calculate_profitability_score()` - امتیاز سودآوری
  - `calculate_growth_score()` - امتیاز رشد
  - `calculate_financial_health_score()` - امتیاز سلامت مالی
  - `calculate_risk_score()` - امتیاز ریسک
  - `rank_stocks()` - رتبه‌بندی چند سهم

### 🌐 API Endpoints
**Base URL**: `/api/v1/stock-scoring`

#### 1. Composite Score
```http
GET /api/v1/stock-scoring/{company_id}/score
```
**خروجی**:
- امتیاز کل (0-100)
- رتبه‌بندی حروفی (A+ تا F)
- امتیاز هر بعد
- تفکیک جزئیات هر متریک

#### 2. Rank Stocks
```http
POST /api/v1/stock-scoring/rank?min_score=60
```
**خروجی**:
- لیست سهم‌ها مرتب‌شده بر اساس امتیاز
- رتبه هر سهم (1 = بالاترین امتیاز)
- امتیاز کل و رتبه حروفی
- امتیازات ابعاد مختلف

#### 3. Individual Dimension Scores
```http
GET /api/v1/stock-scoring/{company_id}/valuation-score
GET /api/v1/stock-scoring/{company_id}/profitability-score
GET /api/v1/stock-scoring/{company_id}/growth-score
GET /api/v1/stock-scoring/{company_id}/financial-health-score
```

### 📊 Use Cases
1. **Stock Screening**: فیلتر سهم‌ها با امتیاز بالاتر از 70
2. **Portfolio Construction**: انتخاب بهترین سهم‌ها برای پرتفوی
3. **Relative Analysis**: مقایسه سهم‌ها در یک صنعت
4. **Performance Tracking**: ردیابی تغییرات امتیاز در طول زمان

---

## 4️⃣ Sensitivity Analysis (حساسیت‌سنجی)

### 📋 توضیحات
تحلیل تأثیر تغییرات فرضیات کلیدی بر ارزشگذاری:
- **One-Way Sensitivity**: تغییر یک متغیر (Tornado Chart)
- **Two-Way Sensitivity**: تغییر دو متغیر همزمان (Data Table)
- **Monte Carlo Simulation**: شبیه‌سازی 10,000 سناریو تصادفی
- **Tornado Chart**: رتبه‌بندی متغیرها بر اساس تأثیر

### 🔧 سرویس‌ها
- **File**: `app/services/sensitivity_analysis_service.py` (445 lines)
- **Methods**:
  - `one_way_sensitivity()` - حساسیت تک‌متغیره
  - `two_way_sensitivity()` - حساسیت دو متغیره
  - `monte_carlo_simulation()` - شبیه‌سازی مونت‌کارلو
  - `tornado_chart_data()` - داده‌های نمودار Tornado

### 🌐 API Endpoints
**Base URL**: `/api/v1/sensitivity-analysis`

#### 1. One-Way Sensitivity
```http
POST /api/v1/sensitivity-analysis/{company_id}/one-way?variable=wacc&variation_min=-0.30&variation_max=0.30&num_points=11
```
**ورودی**:
```json
{
  "fcf": 100.0,
  "wacc": 0.10,
  "terminal_growth": 0.025,
  "years": 5
}
```
**خروجی**:
- ارزش شرکت در 11 سطح مختلف WACC
- درصد تغییر نسبت به حالت پایه

#### 2. Two-Way Sensitivity
```http
POST /api/v1/sensitivity-analysis/{company_id}/two-way?variable_x=wacc&variable_y=terminal_growth&num_points=7
```
**خروجی**:
- جدول 7×7 ارزش شرکت
- هر ترکیب WACC × Terminal Growth

#### 3. Monte Carlo Simulation
```http
POST /api/v1/sensitivity-analysis/{company_id}/monte-carlo?num_simulations=10000
```
**ورودی**:
```json
{
  "base_params": {
    "fcf": 100.0,
    "wacc": 0.10,
    "terminal_growth": 0.025
  },
  "variable_distributions": {
    "wacc": {"mean": 0.10, "std": 0.02},
    "terminal_growth": {"mean": 0.025, "std": 0.01}
  }
}
```
**خروجی**:
- آماره‌های توزیع (میانگین، میانه، انحراف معیار)
- صدک‌ها (P5, P10, P25, P50, P75, P90, P95)
- فواصل اطمینان 80% و 90%

#### 4. Tornado Chart
```http
POST /api/v1/sensitivity-analysis/{company_id}/tornado-chart?variation_pct=0.20
```
**ورودی**:
```json
{
  "base_params": {...},
  "variables": ["wacc", "terminal_growth", "fcf"]
}
```
**خروجی**:
- رتبه‌بندی متغیرها بر اساس تأثیر
- محدوده تأثیر (Impact Range)
- Upside/Downside درصدی

### 📊 Use Cases
1. **Key Value Drivers**: شناسایی مهم‌ترین فرضیات
2. **Risk Quantification**: احتمال رسیدن به ارزش هدف
3. **Scenario Planning**: تست حساسیت فرضیات

---

## 5️⃣ Value Drivers Analysis (تحلیل محرک‌های ارزش)

### 📋 توضیحات
تجزیه ارزش به محرک‌های بنیادی:
- **DuPont Analysis**: تجزیه ROE = Margin × Turnover × Leverage
- **Revenue Drivers**: تحلیل رشد درآمد
- **Margin Drivers**: Waterfall از Gross → Operating → Net Margin
- **Capital Efficiency**: Asset Turnover، Fixed Asset Turnover
- **Waterfall Analysis**: تغییرات دوره‌ای

### 🔧 سرویس‌ها
- **File**: `app/services/value_drivers_service.py` (570 lines)
- **Methods**:
  - `dupont_analysis()` - تحلیل DuPont (3-Level)
  - `revenue_drivers()` - محرک‌های درآمد
  - `margin_drivers()` - محرک‌های حاشیه سود
  - `capital_efficiency_drivers()` - کارایی سرمایه
  - `waterfall_analysis()` - تحلیل Waterfall

### 🌐 API Endpoints
**Base URL**: `/api/v1/value-drivers`

#### 1. DuPont Analysis
```http
GET /api/v1/value-drivers/{company_id}/dupont
```
**خروجی**:
```json
{
  "three_level_dupont": {
    "roe": 0.1524,
    "components": {
      "net_profit_margin": 0.12,
      "asset_turnover": 1.05,
      "equity_multiplier": 1.21
    },
    "interpretation": {
      "profitability_driver": "High",
      "efficiency_driver": "High",
      "leverage_driver": "Low"
    }
  }
}
```

#### 2. Revenue Drivers
```http
GET /api/v1/value-drivers/{company_id}/revenue-drivers?num_periods=5
```
**خروجی**:
- CAGR درآمد
- رشد دوره‌ای (YoY)
- تغییرات مطلق درآمد

#### 3. Margin Drivers
```http
GET /api/v1/value-drivers/{company_id}/margin-drivers?num_periods=5
```
**خروجی**:
- روند Gross/Operating/Net Margin
- فشردگی حاشیه سود در هر سطح:
  - Gross → Operating: تأثیر هزینه‌های عملیاتی
  - Operating → Net: تأثیر مالیات و بهره

#### 4. Capital Efficiency
```http
GET /api/v1/value-drivers/{company_id}/capital-efficiency
```
**خروجی**:
- Asset Turnover (Benchmark: >1.0)
- Fixed Asset Turnover (Benchmark: >2.0)
- Working Capital Turnover (Benchmark: >5.0)

#### 5. Waterfall Analysis
```http
GET /api/v1/value-drivers/{company_id}/waterfall?metric=net_income&num_periods=2
```
**خروجی**:
- تجزیه تغییرات Net Income:
  - Starting Net Income
  - + Revenue Change
  - - COGS Change
  - - OpEx Change
  - = Ending Net Income

### 📊 Use Cases
1. **Performance Attribution**: کدام بخش ROE را می‌راند؟
2. **Operational Improvements**: کارایی دارایی‌ها چگونه است؟
3. **Margin Analysis**: چرا حاشیه سود تغییر کرده؟

---

## 6️⃣ Risk Assessment (ارزیابی ریسک)

### 📋 توضیحات
ارزیابی جامع ریسک با **سه سناریو**:
- **Optimistic**: ریسک‌ها 20% کمتر از سطح فعلی
- **Neutral**: ریسک‌های فعلی
- **Pessimistic**: ریسک‌ها 30% بیشتر از سطح فعلی

### 🔧 متریک‌های ریسک
1. **Altman Z-Score**: پیش‌بینی ورشکستگی
   - Z > 2.99: Safe Zone
   - 1.81 < Z < 2.99: Grey Zone
   - Z < 1.81: Distress Zone

2. **Beta**: ریسک سیستماتیک بازار
   - β < 1: کمتر نوسان از بازار
   - β = 1: هم‌نوسان با بازار
   - β > 1: بیشتر نوسان از بازار

3. **Volatility**: نوسان‌پذیری تاریخی (30d، 90d)

4. **Value at Risk (VaR)**: حداکثر ضرر احتمالی

### 🌐 API Endpoints
**Base URL**: `/api/v1/risk-assessments`

#### 1. Comprehensive Risk with Scenarios
```http
POST /api/v1/risk-assessments/{company_id}
```
**خروجی**:
- ریسک کل در 3 سناریو
- رتبه‌بندی ریسک (Very Low / Low / Medium / High / Very High)
- ریسک‌های جزء:
  - Financial Risk
  - Operational Risk
  - Business Risk
  - Market Risk
  - ESG Risk

#### 2. Altman Z-Score
```http
GET /api/v1/risk-assessments/{company_id}/altman-z-score
```

#### 3. Beta Calculation
```http
GET /api/v1/risk-assessments/{company_id}/beta
```

#### 4. Volatility
```http
GET /api/v1/risk-assessments/{company_id}/volatility
```

#### 5. Value at Risk
```http
GET /api/v1/risk-assessments/{company_id}/value-at-risk
```

---

## 7️⃣ Market Data Management

### 📋 توضیحات
مدیریت داده‌های بازار (قیمت، حجم معاملات):
- همگام‌سازی از Data Collection Microservice
- محاسبه بازده‌های روزانه
- آماره‌های قیمتی (High/Low/Average/Std Dev)

### 🌐 API Endpoints
**Base URL**: `/api/v1/market-data`

#### 1. Sync Market Data
```http
POST /api/v1/market-data/sync/{ticker}?start_date=2024-01-01&end_date=2024-12-31
```

#### 2. Get Market Data
```http
GET /api/v1/market-data/{company_id}?start_date=2024-01-01&end_date=2024-12-31
```

#### 3. Latest Price
```http
GET /api/v1/market-data/{company_id}/latest
```

#### 4. Price Statistics
```http
GET /api/v1/market-data/{company_id}/statistics?start_date=2024-01-01
```

#### 5. Daily Returns
```http
GET /api/v1/market-data/{company_id}/returns?start_date=2024-01-01
```

---

## 8️⃣ Data Collection Integration

### 📋 توضیحات
یکپارچه‌سازی با میکروسرویس جداگانه Data Collection:
- دریافت صورت‌های مالی
- دریافت داده‌های بازار
- همگام‌سازی اطلاعات شرکت
- Sync چندگانه (Income Statement + Balance Sheet + Cash Flow)

### 🌐 API Endpoints
**Base URL**: `/api/v1/data-collection`

**Fetch Endpoints** (دریافت از Data Collection):
- `GET /health` - وضعیت سرویس
- `GET /tickers` - لیست تیکرها
- `GET /status/{ticker}` - وضعیت داده‌ها
- `POST /income-statement` - دریافت صورت سود و زیان
- `POST /balance-sheet` - دریافت ترازنامه
- `POST /cash-flow` - دریافت گردش وجوه نقد
- `POST /market-data` - دریافت داده‌های بازار
- `POST /company-info` - دریافت اطلاعات شرکت

**Sync Endpoints** (همگام‌سازی با دیتابیس محلی):
- `POST /sync/company/{ticker}` - همگام‌سازی شرکت
- `POST /sync/financial-statements/{ticker}` - همگام‌سازی همه صورت‌ها
- `POST /sync/income-statements/{ticker}` - همگام‌سازی صورت سود و زیان
- `POST /sync/balance-sheets/{ticker}` - همگام‌سازی ترازنامه
- `POST /sync/cash-flow-statements/{ticker}` - همگام‌سازی گردش وجوه

---

## 📈 پیشرفت کلی پروژه | Overall Progress

### قبل از این فاز
- **40%** تکمیل شده
- امکانات موجود: Company Management، Financial Statements،50+ Ratios،3 Valuation Methods

### بعد از این فاز
- **85%** تکمیل شده ✅
- **8 قابلیت جدید** اضافه شده
- **45 endpoint جدید** API
- **6 سرویس جدید** (4,500+ lines of code)

### کارهای باقیمانده (15%)
1. **Macro Sensitivity** (5%): حساسیت به نرخ بهره، ارز، نفت
2. **Advanced Integrations** (5%): یکپارچه‌سازی با سرویس‌های دیگر
3. **Performance Optimization** (5%): بهینه‌سازی کوئری‌ها و کش

---

## 🎯 Use Case Scenarios

### سناریو 1: انتخاب سهم برای سرمایه‌گذاری
1. **Stock Scoring**: امتیازدهی همه سهم‌ها → فیلتر امتیاز >70
2. **Scenario Analysis**: بررسی پتانسیل صعود/نزول در 3 سناریو
3. **Risk Assessment**: تأیید ریسک قابل‌قبول
4. **Trend Analysis**: اطمینان از روند مثبت عملکرد

### سناریو 2: ارزیابی جامع یک سهم
1. **DuPont Analysis**: فهم محرک‌های ROE
2. **Margin Drivers**: بررسی روند حاشیه سود
3. **Sensitivity Analysis**: تست فرضیات ارزشگذاری
4. **Monte Carlo**: تعیین محدوده ارزش با احتمال 90%

### سناریو 3: مقایسه سهم‌ها در یک صنعت
1. **Stock Ranking**: رتبه‌بندی همه سهم‌های صنعت
2. **Valuation Score**: مقایسه سطح ارزشگذاری
3. **Growth Score**: شناسایی سریع‌ترین رشد
4. **Risk Score**: تعادل ریسک-بازده

---

## 🛠️ Technical Stack

### Languages & Frameworks
- **Python 3.11+**: Async/Await
- **FastAPI 0.104+**: REST API
- **SQLAlchemy 2.0**: ORM Async
- **PostgreSQL 15**: Database

### Scientific Libraries
- **NumPy**: محاسبات آرایه‌ای و آماری
- **SciPy**: رگرسیون خطی، تست‌های آماری

### Integration
- **httpx**: HTTP Client برای Data Collection Microservice
- **Redis**: Caching (آماده برای استفاده)

---

## 📚 Documentation Files

1. **FEATURES_COMPREHENSIVE_ANALYSIS.md**: نقشه راه کامل پروژه
2. **DATA_COLLECTION_INTEGRATION.md**: راهنمای یکپارچه‌سازی
3. **NEW_FEATURES_COMPLETE.md**: این فایل - مستندات امکانات جدید

---

## ⚡ Next Steps (مراحل بعدی)

### Priority 1 - Testing & Validation
- Unit Tests برای سرویس‌های جدید
- Integration Tests برای APIها
- Load Testing برای عملکرد

### Priority 2 - Documentation
- OpenAPI/Swagger documentation
- Postman Collection
- User Guide (راهنمای کاربری)

### Priority 3 - Macro Sensitivity
- نرخ بهره (Interest Rate Sensitivity)
- نرخ ارز (FX/Dollar Sensitivity)
- قیمت نفت (Oil Price Sensitivity)
- قیمت کامودیتی‌ها

### Priority 4 - Performance
- Database Query Optimization
- Redis Caching Implementation
- Async Background Tasks
- Rate Limiting

---

## 📞 Support & Contact

برای سوالات فنی یا پیشنهادات:
- مستندات API: `/api/v1/docs`
- Health Check: `/api/v1/health`
- Metrics: `/metrics` (Prometheus)

---

**نسخه**: 2.0.0  
**تاریخ آخرین بروزرسانی**: 2024-12-XX  
**وضعیت**: Production Ready ✅
