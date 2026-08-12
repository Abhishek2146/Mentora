"""
Vector store service for syllabus RAG.
"""
import os
import shutil
from typing import List, Optional

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import get_logger
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)


class VectorService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.persist_directory = settings.CHROMA_PERSIST_DIR
        os.makedirs(self.persist_directory, exist_ok=True)

    def create_collection(self, collection_name: str, documents: List[Document]) -> Chroma:
        if not documents:
            raise ValueError("At least one document is required")
        return Chroma.from_documents(
            documents=documents,
            embedding=self.embedding_service.embeddings,
            persist_directory=self.persist_directory,
            collection_name=collection_name,
        )

    def get_collection(self, collection_name: str) -> Chroma:
        return Chroma(
            embedding_function=self.embedding_service.embeddings,
            persist_directory=self.persist_directory,
            collection_name=collection_name,
        )

    def add_documents(self, collection_name: str, documents: List[Document]) -> Chroma:
        if not documents:
            return self.get_collection(collection_name)
        vector_db = self.get_collection(collection_name)
        vector_db.add_documents(documents)
        return vector_db

    def similarity_search(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> List[Document]:
        vector_db = self.get_collection(collection_name)
        return vector_db.similarity_search(query, k=k, filter=filter)

    def delete_collection(self, collection_name: str) -> None:
        # Chroma collections are stored inside a shared persistence directory;
        # deleting a collection directory manually is unsafe. Use the Chroma API.
        vector_db = self.get_collection(collection_name)
        vector_db.delete_collection()
        logger.info("Deleted collection: %s", collection_name)
