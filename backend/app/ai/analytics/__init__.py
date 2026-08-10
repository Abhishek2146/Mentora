"""
Analytics module - AI-powered learning analytics
"""
from app.services.analytics_service import AnalyticsService

analytics_engine = AnalyticsService()

__all__ = ["analytics_engine", "AnalyticsService"]
