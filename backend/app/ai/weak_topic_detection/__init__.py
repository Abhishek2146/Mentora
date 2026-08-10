"""
Weak Topic Detection module
"""
from app.services.progress_service import ProgressService

weak_topic_detector = ProgressService()

__all__ = ["weak_topic_detector", "ProgressService"]
