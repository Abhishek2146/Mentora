"""
Embedding Service for Mentora RAG.

Uses a local Sentence Transformers model.
No OpenAI API is required.
"""

from typing import List

from sentence_transformers import SentenceTransformer
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(__name__)


class EmbeddingService:
    """
    Generates text embeddings locally using Sentence Transformers.
    """

    def __init__(self):
        self.model_name = getattr(
            settings,
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )

        logger.info(
            "Loading embedding model: %s",
            self.model_name,
        )

        self.model = SentenceTransformer(self.model_name)

        self._embeddings = HuggingFaceEmbeddings(
            model_name=self.model_name,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

        logger.info("Embedding model loaded successfully.")

    @property
    def embeddings(self):
        """Return a langchain-compatible embeddings instance."""
        return self._embeddings

    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.
        """

        if not text or not text.strip():
            return []

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
        )

        return embedding.tolist()

    def embed_documents(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        """

        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return self._embeddings.embed_documents(texts)

    def similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """
        Calculate cosine similarity between two texts.
        """

        from sklearn.metrics.pairwise import cosine_similarity

        embedding1 = self.model.encode(
            [text1],
            convert_to_numpy=True,
        )

        embedding2 = self.model.encode(
            [text2],
            convert_to_numpy=True,
        )

        return float(
            cosine_similarity(
                embedding1,
                embedding2,
            )[0][0]
        )

    def split_text(self, text: str) -> List[Document]:
        """Split text into chunks for embedding."""
        return self.text_splitter.create_documents([text])
