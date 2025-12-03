"""
Monitoring package for EPUP system

Contains:
- KPI definitions and calculations
- Scheduled health checks
- Alert management
"""

from .kpi_definitions import EPUPKPICalculator

__all__ = ["EPUPKPICalculator"]
