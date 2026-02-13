"""Dashboard module for compliance coverage metrics computation."""

from .coverage import CoverageComputer, DomainCoverage, LawCoverage
from .metrics import MetricsAggregator, DashboardStats

__all__ = [
    "CoverageComputer",
    "DomainCoverage",
    "LawCoverage",
    "MetricsAggregator",
    "DashboardStats",
]
