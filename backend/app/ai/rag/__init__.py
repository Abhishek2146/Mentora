"""
RAG module - Retrieval-Augmented Generation
"""
from app.services.vector_service import VectorService, EmbeddingService

vector_service = VectorService()
embedding_service = EmbeddingService()

__all__ = ["vector_service", "embedding_service", "VectorService", "EmbeddingService"]
