"""
Embedding and Vector Service
"""
import json
from typing import List, Optional, Dict, Any

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


from app.services.embedding_service import EmbeddingService


class VectorService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.persist_directory = settings.CHROMA_PERSIST_DIR
        self._ensure_directory()

    def _ensure_directory(self):
        import os
        os.makedirs(self.persist_directory, exist_ok=True)

    def create_collection(self, collection_name: str, documents: List[Document]) -> Chroma:
        """Create a ChromaDB collection with documents."""
        vector_db = Chroma.from_documents(
            documents=documents,
            embedding=self.embedding_service.embeddings,
            persist_directory=self.persist_directory,
            collection_name=collection_name,
        )
        vector_db.persist()
        logger.info(f"Created collection: {collection_name}")
        return vector_db

    def get_collection(self, collection_name: str) -> Chroma:
        """Get an existing ChromaDB collection."""
        vector_db = Chroma(
            embedding=self.embedding_service.embeddings,
            persist_directory=self.persist_directory,
            collection_name=collection_name,
        )
        return vector_db

    def add_documents(self, collection_name: str, documents: List[Document]) -> Chroma:
        """Add documents to an existing collection."""
        vector_db = self.get_collection(collection_name)
        vector_db.add_documents(documents)
        vector_db.persist()
        return vector_db

    def similarity_search(
        self, collection_name: str, query: str, k: int = 5, filter: Optional[dict] = None
    ) -> List[Document]:
        """Perform similarity search on a collection."""
        vector_db = self.get_collection(collection_name)
        results = vector_db.similarity_search(query, k=k, filter=filter)
        return results

    def delete_collection(self, collection_name: str):
        """Delete a collection."""
        import shutil
        collection_path = os.path.join(self.persist_directory, collection_name)
        if os.path.exists(collection_path):
            shutil.rmtree(collection_path)
        logger.info(f"Deleted collection: {collection_name}")
