"""
Embedding Service
"""
import os
from typing import List, Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    # Class-level cache: the HuggingFace model is loaded once per process
    # and shared across every EmbeddingService instance (TutorService,
    # SyllabusService, QuizService, etc. each create their own
    # EmbeddingService, but they must not each trigger a separate model
    # load/download).
    _shared_embeddings: Optional[HuggingFaceEmbeddings] = None

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        if EmbeddingService._shared_embeddings is None:
            logger.info(f"Loading local embedding model: {settings.EMBEDDING_MODEL}")
            EmbeddingService._shared_embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
            )
        return EmbeddingService._shared_embeddings

    def split_text(self, text: str) -> List[Document]:
        """Split text into chunks for embedding."""
        return self.text_splitter.create_documents([text])

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into smaller chunks."""
        return self.text_splitter.split_documents(documents)

    def chunk_text_with_metadata(
        self, text: str, base_metadata: dict
    ) -> List[Document]:
        """Split raw text into chunks and attach shared metadata plus a
        per-chunk ``chunk_index`` to each resulting Document.

        ``base_metadata`` should only contain fields that genuinely exist
        (e.g. user_id, syllabus_id, source) - this method does not invent
        any values, it just stamps them onto every chunk along with the
        chunk's position in the sequence.
        """
        if not text or not text.strip():
            return []

        chunks = self.text_splitter.create_documents([text])
        for index, chunk in enumerate(chunks):
            chunk.metadata.update(base_metadata)
            chunk.metadata["chunk_index"] = index
        return chunks

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embeddings.embed_query(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return self.embeddings.embed_documents(texts)