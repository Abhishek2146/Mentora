"""
Revision module - AI-powered revision scheduling
"""
from app.services.revision_service import RevisionService

revision_engine = RevisionService()

__all__ = ["revision_engine", "RevisionService"]
