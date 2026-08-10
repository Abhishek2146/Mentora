"""
Embedding Service
"""
import os
from typing import List

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-small",
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

    def split_text(self, text: str) -> List[Document]:
        """Split text into chunks for embedding."""
        return self.text_splitter.create_documents([text])

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into smaller chunks."""
        return self.text_splitter.split_documents(documents)

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embeddings.embed_query(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return self.embeddings.embed_queries(texts)
