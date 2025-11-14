# 🔧 مشکلات و TODO لیست میکروسرویس

تاریخ ایجاد: 2025-01-14  
وضعیت: در حال بررسی و رفع مشکلات

---

## 📋 خلاصه مشکلات شناسایی شده

| دسته | تعداد مشکلات | اولویت | وضعیت |
|------|-------------|---------|-------|
| Dependencies | 6 | 🔴 بحرانی | در انتظار رفع |
| Tests Coverage | 8 | 🟡 متوسط | در انتظار رفع |
| Logging | 10 | 🟢 پایین | در انتظار رفع |
| Documentation | 5 | 🟡 متوسط | در انتظار رفع |
| API Integration | 4 | 🟡 متوسط | در انتظار رفع |
| Code Quality | 7 | 🟢 پایین | در انتظار رفع |
| **جمع کل** | **40** | - | - |

---

## 🔴 مشکلات بحرانی (Priority 1)

### 1. Dependencies مفقود شده

**مشکل:** پکیج‌های ضروری ML در `pyproject.toml` وجود ندارند

**فایل‌های تاثیر گرفته:**
- `app/services/ml_dataset_builder.py` (pandas)
- `app/services/valuation_prediction_model.py` (torch, pytorch)
- `app/services/valuation_performance.py` (pandas)
- `app/services/report_generator.py` (reportlab, matplotlib)
- `app/services/valuation_scenarios.py` (scipy)

**خطاها:**
```
Import "pandas" could not be resolved from source
Import "torch" could not be resolved
Import "reportlab.lib.pagesizes" could not be resolved
Import "matplotlib.pyplot" could not be resolved
Import "scipy" could not be resolved
```

**راه حل:**
```toml
# اضافه کردن به pyproject.toml:
pandas = "^2.1.3"          # ✅ موجود
torch = "^2.1.0"           # ❌ مفقود
reportlab = "^4.0.7"       # ❌ مفقود
matplotlib = "^3.8.2"      # ❌ مفقود
scipy = "^1.11.4"          # ✅ موجود
```

**زمان تخمینی:** 30 دقیقه  
**مسئول:** DevOps Engineer

---

### 2. Test Coverage برای سرویس‌های ML جدید

**مشکل:** 10 سرویس جدید ML بدون تست

**فایل‌های بدون تست:**
1. `app/services/ml_dataset_builder.py` (585 lines) ❌
2. `app/services/valuation_prediction_model.py` (614 lines) ❌
3. `app/services/prediction_tracking.py` (150 lines) ❌
4. `app/services/scenario_tracker.py` (430 lines) ❌
5. `app/services/valuation_performance.py` (478 lines) ❌
6. `app/services/mispricing_detector.py` (537 lines) ❌
7. `app/services/valuation_ensemble.py` (531 lines) ❌
8. `app/api/v1/endpoints/valuation_scenarios.py` (564 lines) ❌
9. `app/services/report_generator.py` (612 lines) ❌
10. `app/services/valuation_features.py` (موجود) ⚠️ نیاز به بررسی

**هدف Test Coverage:** 95%+

**زمان تخمینی:** 40 ساعت (4h per service × 10)  
**مسئول:** Testing Engineer

---

### 3. Database Migration برای جداول جدید

**مشکل:** جداول `prediction_tracking.py` در Alembic نیست

**جداول جدید:**
- `valuation_predictions` (schema: tse)
- `prediction_outcomes` (schema: tse)

**راه حل:**
```bash
alembic revision --autogenerate -m "add prediction tracking tables"
alembic upgrade head
```

**زمان تخمینی:** 1 ساعت  
**مسئول:** Backend Developer

---

### 4. Data Collection Integration واقعی

**مشکل:** سرویس‌های جدید از placeholder استفاده می‌کنند

**فایل‌های نیاز به Integration:**
- `app/services/ml_dataset_builder.py` (line 150-200: mock data)
- `app/services/valuation_ensemble.py` (line 450: mock regime detection)
- `app/api/v1/endpoints/valuation_scenarios.py` (line 500+: mock valuations)

**راه حل:**
- اتصال به `DataIntegrationService`
- استفاده از داده‌های واقعی financial statements
- حذف mock data

**زمان تخمینی:** 12 ساعت  
**مسئول:** Integration Engineer

---

### 5. ML Model Training Pipeline

**مشکل:** مدل ML هنوز train نشده

**نیازمندی‌ها:**
1. ✅ Dataset builder (موجود)
2. ✅ Model architecture (موجود)
3. ❌ Training script
4. ❌ Evaluation script
5. ❌ Model versioning
6. ❌ Model deployment

**راه حل:**
ایجاد:
- `scripts/train_ml_model.py` - Training pipeline
- `scripts/evaluate_model.py` - Evaluation
- `models/` directory - Stored models
- CI/CD integration

**زمان تخمینی:** 16 ساعت  
**مسئول:** ML Engineer

---

### 6. API Authentication/Authorization

**مشکل:** Endpoint های جدید بدون authentication

**فایل‌ها:**
- `app/api/v1/endpoints/valuation_scenarios.py`
  - `get_current_tenant` dependency موجود ✅
  - اما نیاز به `get_current_user` برای rate limiting

**راه حل:**
```python
from app.core.security import get_current_user

@router.post("/what-if")
async def what_if_scenario_analysis(
    request: WhatIfRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # ✅ اضافه کردن
    tenant_id: str = Depends(get_current_tenant)
):
```

**زمان تخمینی:** 3 ساعت  
**مسئول:** Security Engineer

---

## 🟡 مشکلات متوسط (Priority 2)

### 7. Logging استاندارد نشده

**مشکل:** سرویس‌های جدید از `logging` استفاده می‌کنند، نه `structlog`

**فایل‌های تاثیر گرفته:**
- `app/services/valuation_prediction_model.py`
- `app/services/scenario_tracker.py`
- `app/services/valuation_performance.py`
- و 7 فایل دیگر

**مشکل فعلی:**
```python
import logging
logger = logging.getLogger(__name__)  # ❌ غیراستاندارد
```

**راه حل:**
```python
import structlog
logger = structlog.get_logger()  # ✅ استاندارد
```

**زمان تخمینی:** 2 ساعت  
**مسئول:** DevOps Engineer

---

### 8. Documentation API (OpenAPI/Swagger)

**مشکل:** Endpoint های جدید نیاز به بهبود documentation دارند

**فایل:**
- `app/api/v1/endpoints/valuation_scenarios.py`

**نیازمندی‌ها:**
- ✅ Docstrings موجود
- ⚠️ Example requests/responses کامل نیست
- ❌ Tags برای grouping
- ❌ Response models کامل

**راه حل:**
```python
@router.post(
    "/what-if",
    response_model=WhatIfResponse,
    tags=["Scenario Analysis"],
    summary="Perform what-if scenario analysis",
    responses={
        200: {"description": "Successful analysis"},
        404: {"description": "Company not found"},
        422: {"description": "Validation error"}
    }
)
```

**زمان تخمینی:** 4 ساعت  
**مسئول:** Technical Writer

---

### 9. Error Handling در ML Services

**مشکل:** Exception handling ناقص

**فایل‌های نیاز به بهبود:**
- `app/services/ml_dataset_builder.py` - خطاهای I/O
- `app/services/valuation_prediction_model.py` - خطاهای model loading
- `app/services/report_generator.py` - خطاهای PDF generation

**راه حل:**
```python
from app.core.exceptions import ValidationError, ServiceError

try:
    result = await self.train_model()
except FileNotFoundError as e:
    raise ServiceError(f"Model file not found: {e}")
except torch.OutOfMemoryError:
    raise ServiceError("Insufficient memory for training")
```

**زمان تخمینی:** 6 ساعت  
**مسئول:** Backend Developer

---

### 10. Caching Strategy برای ML Predictions

**مشکل:** ML inference بدون cache (هر بار recalculate)

**فایل:**
- `app/services/valuation_prediction_model.py`

**راه حل:**
```python
from app.services.cache_service import CacheService

async def predict(self, features: np.ndarray) -> Dict:
    cache_key = f"ml_prediction:{hash(features.tobytes())}"
    cached = await self.cache.get(cache_key)
    
    if cached:
        return cached
    
    prediction = self._do_prediction(features)
    await self.cache.set(cache_key, prediction, ttl=3600)  # 1 hour
    return prediction
```

**زمان تخمینی:** 4 ساعت  
**مسئول:** Backend Developer

---

### 11. Monitoring/Metrics برای ML Services

**مشکل:** Prometheus metrics برای ML workflow نیست

**نیازمندی‌ها:**
- ML inference time
- Prediction accuracy (real-time)
- Dataset build time
- Model training progress
- Cache hit rate

**راه حل:**
```python
from prometheus_client import Histogram, Counter

ml_inference_duration = Histogram(
    'ml_inference_duration_seconds',
    'Time spent on ML inference',
    ['model_version']
)

ml_predictions_total = Counter(
    'ml_predictions_total',
    'Total ML predictions made',
    ['model_version', 'outcome']
)
```

**زمان تخمینی:** 5 ساعت  
**مسئول:** DevOps Engineer

---

### 12. Data Validation برای ML Inputs

**مشکل:** Input validation ناکافی

**فایل:**
- `app/services/ml_dataset_builder.py`
- `app/services/valuation_prediction_model.py`

**راه حل:**
```python
from pydantic import BaseModel, Field, validator

class MLPredictionInput(BaseModel):
    features: List[float] = Field(..., min_items=130, max_items=130)
    
    @validator('features')
    def validate_features(cls, v):
        if any(x < -100 or x > 100 for x in v):
            raise ValueError("Features out of range")
        return v
```

**زمان تخمینی:** 3 ساعت  
**مسئول:** Backend Developer

---

### 13. Integration Tests برای ML Pipeline

**مشکل:** فقط unit tests، integration tests نیست

**نیاز:**
```
tests/integration/
├── test_ml_pipeline_end_to_end.py      # ❌ مفقود
├── test_prediction_feedback_loop.py    # ❌ مفقود
├── test_ensemble_integration.py        # ❌ مفقود
└── test_scenario_api_integration.py    # ❌ مفقود
```

**زمان تخمینی:** 12 ساعت  
**مسئول:** Testing Engineer

---

### 14. Performance Benchmarks

**مشکل:** Performance requirements مشخص نیست

**نیازمندی‌ها:**
- ML inference: <10ms (ذکر شده ✅)
- Dataset build: <5 min for 100K rows (نیاز به تست ❌)
- PDF generation: <2 sec (نیاز به تست ❌)
- Scenario API: <500ms (نیاز به تست ❌)

**راه حل:**
ایجاد:
- `tests/performance/test_ml_performance.py`
- Load tests با Locust
- Benchmarking suite

**زمان تخمینی:** 8 ساعت  
**مسئول:** Performance Engineer

---

## 🟢 مشکلات پایین اولویت (Priority 3)

### 15. Code Duplication

**مشکل:** کدهای تکراری در چند سرویس

**مثال:**
- Calculation helpers در `valuation_ensemble.py` و `mispricing_detector.py`
- Data fetching در ML services

**راه حل:**
ایجاد:
- `app/utils/ml_helpers.py` - Shared ML utilities
- `app/utils/calculation_helpers.py` - Common calculations

**زمان تخمینی:** 4 ساعت  
**مسئول:** Senior Developer

---

### 16. Type Hints کامل نیست

**مشکل:** بعضی توابع بدون type hints

**فایل‌های نیاز به بهبود:**
- `app/services/report_generator.py` (بخش chart generation)
- `app/services/valuation_ensemble.py` (helper methods)

**راه حل:**
```python
# Before ❌
def calculate_score(value, baseline):
    return (value - baseline) / baseline

# After ✅
def calculate_score(value: float, baseline: float) -> float:
    return (value - baseline) / baseline
```

**زمان تخمینی:** 3 ساعت  
**مسئول:** Junior Developer

---

### 17. Docstrings بهبود

**مشکل:** Docstrings موجود اما می‌تواند کامل‌تر باشد

**نیازمندی‌ها:**
- ✅ Function/class descriptions موجود
- ⚠️ Parameters بعضی جاها ناقص
- ❌ Returns بعضی جاها مفقود
- ❌ Raises بیشتر جاها مفقود
- ❌ Examples کم است

**راه حل:**
```python
def calculate_consensus(
    self,
    valuations: Dict[str, float],
    weights: List[MethodWeight]
) -> float:
    """
    Calculate weighted consensus fair value.
    
    Args:
        valuations: Dict mapping method names to fair values
        weights: List of MethodWeight objects with final_weight
    
    Returns:
        float: Weighted average consensus value
    
    Raises:
        ValueError: If weights don't sum to 1.0 or valuations is empty
    
    Examples:
        >>> calc.calculate_consensus(
        ...     {"DCF": 100, "PE": 110},
        ...     [MethodWeight("DCF", 0.6), MethodWeight("PE", 0.4)]
        ... )
        104.0
    """
```

**زمان تخمینی:** 6 ساعت  
**مسئول:** Technical Writer

---

### 18. Environment Variables برای ML Config

**مشکل:** ML hyperparameters hardcoded

**فایل:**
- `app/services/valuation_prediction_model.py`

**راه حل:**
```python
# app/core/config.py
class Settings(BaseSettings):
    # ML Configuration
    ml_batch_size: int = Field(64, env="ML_BATCH_SIZE")
    ml_learning_rate: float = Field(0.001, env="ML_LEARNING_RATE")
    ml_max_epochs: int = Field(100, env="ML_MAX_EPOCHS")
    ml_model_path: str = Field("models/", env="ML_MODEL_PATH")
```

**زمان تخمینی:** 2 ساعت  
**مسئول:** DevOps Engineer

---

### 19. README/Documentation بروزرسانی

**مشکل:** README شامل فیچرهای جدید ML نیست

**نیاز به اضافه شدن:**
- ML prediction capabilities
- Scenario analysis API
- Report generation
- Ensemble valuation
- Mispricing detection

**زمان تخمینی:** 3 ساعت  
**مسئول:** Technical Writer

---

### 20. Docker Configuration برای ML

**مشکل:** Dockerfile نیاز به PyTorch/ML dependencies

**راه حل:**
```dockerfile
# Use CUDA base image if GPU needed
FROM python:3.11-slim

# Install system dependencies for ML
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch (CPU version)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy and install requirements
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev
```

**زمان تخمینی:** 2 ساعت  
**مسئول:** DevOps Engineer

---

## 📊 آمار کلی

### خلاصه زمان تخمینی:

| دسته | ساعت |
|------|------|
| 🔴 بحرانی | 72.5 ساعت |
| 🟡 متوسط | 48 ساعت |
| 🟢 پایین | 20 ساعت |
| **جمع** | **140.5 ساعت** |

### تقسیم کار بر اساس نقش:

| نقش | تعداد Task | ساعت |
|-----|-----------|------|
| Backend Developer | 8 | 42 |
| Testing Engineer | 3 | 52 |
| ML Engineer | 2 | 24 |
| DevOps Engineer | 5 | 14.5 |
| Integration Engineer | 1 | 12 |
| Security Engineer | 1 | 3 |
| Technical Writer | 3 | 13 |
| Senior Developer | 1 | 4 |
| Performance Engineer | 1 | 8 |
| **جمع** | **25** | **140.5** |

---

## 🎯 اولویت‌بندی برای اجرا

### فاز 1: Critical Fixes (1 هفته)
1. ✅ Dependencies را نصب کن
2. ✅ Database migrations اجرا کن
3. ✅ Authentication/Authorization رو اضافه کن
4. ✅ Basic tests برای سرویس‌های جدید

**زمان:** 40 ساعت (1 هفته با تیم 5 نفره)

### فاز 2: ML Pipeline Ready (2 هفته)
1. ✅ Data integration واقعی
2. ✅ ML training pipeline
3. ✅ Error handling & logging
4. ✅ Caching strategy
5. ✅ Integration tests

**زمان:** 50 ساعت (2 هفته)

### فاز 3: Production Ready (1 هفته)
1. ✅ Full test coverage
2. ✅ Performance benchmarks
3. ✅ Monitoring/metrics
4. ✅ Documentation
5. ✅ Docker optimization

**زمان:** 50 ساعت (1 هفته)

---

## ✅ Checklist تکمیل

- [ ] Dependencies نصب شده
- [ ] Database migrations اجرا شده
- [ ] Tests coverage >95%
- [ ] Authentication کامل
- [ ] Logging استاندارد
- [ ] Error handling کامل
- [ ] Caching پیاده‌سازی شده
- [ ] Monitoring/metrics فعال
- [ ] Integration tests موجود
- [ ] Performance benchmarks تایید شده
- [ ] Documentation بروز
- [ ] Docker image optimized
- [ ] CI/CD pipeline آماده
- [ ] ML model trained
- [ ] Production deployment tested

---

**تاریخ بروزرسانی:** 2025-01-14  
**نسخه:** 1.0.0  
**وضعیت پروژه:** در حال رفع مشکلات
