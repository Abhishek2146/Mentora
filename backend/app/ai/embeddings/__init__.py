"""
Embeddings module
"""
from app.services.embedding_service import EmbeddingService

embedding_service = EmbeddingService()

__all__ = ["embedding_service", "EmbeddingService"]
