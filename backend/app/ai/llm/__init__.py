"""
LLM module - Language Model integrations
"""
from app.services.llm_service import LLMService

llm_service = LLMService()

__all__ = ["llm_service", "LLMService"]
