"""
ML Model Weights Database Models.

Stores dynamic model weights that are updated daily based on performance.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Numeric, Boolean, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base


class MLModelWeights(Base):
    """
    Dynamic model weights learned by ML system.
    
    Updated daily based on historical accuracy.
    """
    
    __tablename__ = "ml_model_weights"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Metadata
    effective_date = Column(DateTime, nullable=False, index=True, 
                           comment="تاریخ اعمال وزن‌ها / Effective date for these weights")
    is_active = Column(Boolean, nullable=False, default=True, index=True,
                      comment="آیا این وزن‌ها فعال هستند / Are these weights currently active")
    
    # Model weights (sum = 1.0)
    dcf_weight = Column(Numeric(10, 6), nullable=False,
                       comment="وزن مدل DCF / DCF model weight")
    rim_weight = Column(Numeric(10, 6), nullable=False,
                       comment="وزن مدل RIM / Residual Income Model weight")
    eva_weight = Column(Numeric(10, 6), nullable=False,
                       comment="وزن مدل EVA / Economic Value Added weight")
    graham_weight = Column(Numeric(10, 6), nullable=False,
                          comment="وزن Graham Number / Graham Number weight")
    peter_lynch_weight = Column(Numeric(10, 6), nullable=False,
                               comment="وزن Peter Lynch / Peter Lynch weight")
    ncav_weight = Column(Numeric(10, 6), nullable=False,
                        comment="وزن NCAV / Net Current Asset Value weight")
    ps_ratio_weight = Column(Numeric(10, 6), nullable=False,
                            comment="وزن P/S / Price/Sales ratio weight")
    pcf_ratio_weight = Column(Numeric(10, 6), nullable=False,
                             comment="وزن P/CF / Price/Cash Flow ratio weight")
    
    # Performance metrics
    training_accuracy = Column(Numeric(5, 4), nullable=True,
                              comment="دقت در آموزش / Training accuracy (0-1)")
    validation_accuracy = Column(Numeric(5, 4), nullable=True,
                                comment="دقت در اعتبارسنجی / Validation accuracy (0-1)")
    backtest_mape = Column(Numeric(5, 4), nullable=True,
                          comment="خطای درصدی مطلق میانگین / Mean Absolute Percentage Error")
    improvement_vs_previous = Column(Numeric(5, 4), nullable=True,
                                    comment="بهبود نسبت به قبل / Improvement vs previous weights")
    
    # Training details
    training_samples = Column(Numeric(10, 0), nullable=True,
                             comment="تعداد نمونه‌های آموزش / Number of training samples")
    training_start_date = Column(DateTime, nullable=True,
                                comment="تاریخ شروع داده آموزش / Training data start date")
    training_end_date = Column(DateTime, nullable=True,
                              comment="تاریخ پایان داده آموزش / Training data end date")
    epochs_trained = Column(Numeric(5, 0), nullable=True,
                           comment="تعداد epoch های آموزش / Number of epochs trained")
    
    # A/B test results
    ab_test_passed = Column(Boolean, nullable=True,
                           comment="آیا تست A/B را پاس کرد / Did pass A/B test")
    ab_test_p_value = Column(Numeric(10, 8), nullable=True,
                            comment="p-value تست A/B / A/B test p-value")
    
    # Deployment info
    deployed_at = Column(DateTime, nullable=True,
                        comment="زمان استقرار / Deployment timestamp")
    deployed_by = Column(String(255), nullable=True,
                        comment="استقرار توسط (system/manual) / Deployed by")
    
    # Additional metadata
    model_version = Column(String(50), nullable=True,
                          comment="نسخه مدل ML / ML model version")
    training_config = Column(JSON, nullable=True,
                            comment="پیکربندی آموزش / Training configuration")
    notes = Column(Text, nullable=True,
                  comment="یادداشت‌ها / Notes")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_ml_weights_effective_active', 'effective_date', 'is_active'),
        Index('idx_ml_weights_deployed', 'deployed_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'is_active': self.is_active,
            'weights': {
                'dcf': float(self.dcf_weight),
                'rim': float(self.rim_weight),
                'eva': float(self.eva_weight),
                'graham': float(self.graham_weight),
                'peter_lynch': float(self.peter_lynch_weight),
                'ncav': float(self.ncav_weight),
                'ps_ratio': float(self.ps_ratio_weight),
                'pcf_ratio': float(self.pcf_ratio_weight),
            },
            'performance': {
                'training_accuracy': float(self.training_accuracy) if self.training_accuracy else None,
                'validation_accuracy': float(self.validation_accuracy) if self.validation_accuracy else None,
                'backtest_mape': float(self.backtest_mape) if self.backtest_mape else None,
                'improvement': float(self.improvement_vs_previous) if self.improvement_vs_previous else None,
            },
            'deployed_at': self.deployed_at.isoformat() if self.deployed_at else None,
        }


class MLModelPerformance(Base):
    """
    Daily performance tracking for each valuation model.
    
    Tracks actual vs predicted prices to measure model accuracy over time.
    """
    
    __tablename__ = "ml_model_performance"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Reference
    company_id = Column(PGUUID(as_uuid=True), nullable=False, index=True,
                       comment="شناسه شرکت / Company ID")
    valuation_date = Column(DateTime, nullable=False, index=True,
                           comment="تاریخ ارزش‌گذاری / Valuation date")
    measurement_date = Column(DateTime, nullable=False, index=True,
                             comment="تاریخ اندازه‌گیری دقت (معمولاً 90 روز بعد) / Accuracy measurement date")
    
    # Model predictions
    dcf_prediction = Column(Numeric(20, 2), nullable=True)
    rim_prediction = Column(Numeric(20, 2), nullable=True)
    eva_prediction = Column(Numeric(20, 2), nullable=True)
    graham_prediction = Column(Numeric(20, 2), nullable=True)
    peter_lynch_prediction = Column(Numeric(20, 2), nullable=True)
    ncav_prediction = Column(Numeric(20, 2), nullable=True)
    ps_ratio_prediction = Column(Numeric(20, 2), nullable=True)
    pcf_ratio_prediction = Column(Numeric(20, 2), nullable=True)
    
    # Ensemble prediction
    ensemble_prediction = Column(Numeric(20, 2), nullable=True,
                                comment="پیش‌بینی ترکیبی / Ensemble prediction")
    
    # Actual outcome
    actual_price = Column(Numeric(20, 2), nullable=True,
                         comment="قیمت واقعی / Actual market price")
    
    # Errors (for each model)
    dcf_error = Column(Numeric(10, 4), nullable=True,
                      comment="خطا DCF / DCF error %")
    rim_error = Column(Numeric(10, 4), nullable=True)
    eva_error = Column(Numeric(10, 4), nullable=True)
    graham_error = Column(Numeric(10, 4), nullable=True)
    peter_lynch_error = Column(Numeric(10, 4), nullable=True)
    ncav_error = Column(Numeric(10, 4), nullable=True)
    ps_ratio_error = Column(Numeric(10, 4), nullable=True)
    pcf_ratio_error = Column(Numeric(10, 4), nullable=True)
    ensemble_error = Column(Numeric(10, 4), nullable=True)
    
    # Which model was most accurate
    best_model = Column(String(50), nullable=True,
                       comment="بهترین مدل / Best performing model")
    worst_model = Column(String(50), nullable=True,
                        comment="بدترین مدل / Worst performing model")
    
    # Weights used at time of prediction
    weights_snapshot = Column(JSON, nullable=True,
                             comment="وزن‌های استفاده شده / Weights used")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_ml_perf_company_date', 'company_id', 'valuation_date'),
        Index('idx_ml_perf_measurement', 'measurement_date'),
    )
