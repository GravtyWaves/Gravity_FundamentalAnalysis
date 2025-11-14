"""
================================================================================
FILE IDENTITY CARD (شناسنامه فایل)
================================================================================
File Path:           app/middleware/__init__.py
Author:              Gravity Fundamental Analysis Team
Team ID:             FA-001
Created Date:        2025-01-20
Last Modified:       2025-01-20
Version:             1.0.0
Purpose:             Middleware package initialization

Dependencies:        None

Related Files:       app/middleware/logging.py (logging middleware)
                     app/main.py (middleware registration)

Complexity:          1/10
Lines of Code:       35
Test Coverage:       N/A
Performance Impact:  LOW
Time Spent:          0.5 hours
Cost:                $240 (0.5 × $480/hr)
Review Status:       In Progress (Task 2)
Notes:               - Middleware package for request/response processing
                     - Future: Add resilience middleware (Circuit Breaker, Retry)
================================================================================
"""

# Middleware package
__all__ = ["setup_logging"]
