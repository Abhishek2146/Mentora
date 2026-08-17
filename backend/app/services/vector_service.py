"""
Embedding and Vector Service
"""
import json
import os
import re
from typing import List, Optional, Dict, Any

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

    @staticmethod
    def collection_name_for_syllabus(syllabus_id: int) -> str:
        """Build the Chroma collection name for a syllabus, tagged with a
        short suffix derived from the configured embedding model.

        This guarantees that switching EMBEDDING_MODEL (e.g. from an
        OpenAI embedding to a local HuggingFace one) never mixes vectors
        from different embedding spaces in the same collection - it just
        transparently starts writing to a new, separate collection.
        Any previously-created collection under the old name is left
        untouched on disk (not deleted); re-uploading/reprocessing the
        syllabus is what populates the new one.
        """
        tag = re.sub(r"[^a-zA-Z0-9]+", "-", settings.EMBEDDING_MODEL).strip("-").lower()
        return f"syllabus_{syllabus_id}_{tag}"

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
            collection_metadata={"hnsw:space": "cosine"},
        )
        vector_db.persist()
        logger.info(f"Created collection: {collection_name}")
        return vector_db

    def get_collection(self, collection_name: str) -> Chroma:
        """Get an existing ChromaDB collection."""
        vector_db = Chroma(
            embedding_function=self.embedding_service.embeddings,
            persist_directory=self.persist_directory,
            collection_name=collection_name,
            collection_metadata={"hnsw:space": "cosine"},
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

    def retrieve_context(
        self,
        collection_name: str,
        query: str,
        k: Optional[int] = None,
        filter: Optional[dict] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Document]:
        """Retrieve relevant chunks for RAG, filtered by relevance score and
        de-duplicated by content.

        This is the retrieval path used by the AI Tutor and Voice Tutor.
        Falls back gracefully (returns []) if the collection doesn't exist
        or has no vectors yet, rather than raising.
        """
        top_k = k if k is not None else settings.RAG_TOP_K
        threshold = (
            score_threshold if score_threshold is not None else settings.RAG_SIMILARITY_THRESHOLD
        )

        vector_db = self.get_collection(collection_name)

        logger.debug(
            "[VectorService] retrieve_context: collection=%s, query=%r, "
            "k=%d, filter=%s, threshold=%s",
            collection_name,
            query[:100],
            top_k,
            filter,
            threshold,
        )

        try:
            scored = vector_db.similarity_search_with_relevance_scores(
                query, k=top_k, filter=filter
            )
        except Exception as e:
            logger.warning(
                "[VectorService] Retrieval failed for collection '%s': %s",
                collection_name,
                e,
            )
            return []

        logger.debug(
            "[VectorService] Retrieved %d candidate documents from '%s'",
            len(scored),
            collection_name,
        )

        seen_content = set()
        results: List[Document] = []
        for doc, score in scored:
            logger.debug(
                "[VectorService] doc score=%s, metadata=%s, content_len=%d",
                score,
                doc.metadata,
                len(doc.page_content),
            )

            # Cosine similarity (used by sentence-transformers) can return
            # negative values in the range [-1, 1] when using relevance
            # scores (1 - cosine_distance).  Normalize to [0, 1] so the
            # threshold comparison is meaningful: 0 = no relation,
            # 0.5 = orthogonal, 1 = identical.
            if score is not None:
                normalized_score = (score + 1.0) / 2.0
                normalized_score = max(0.0, min(1.0, normalized_score))
                logger.debug(
                    "[VectorService] normalized_score=%.4f (raw=%.4f, "
                    "threshold=%s)",
                    normalized_score,
                    score,
                    threshold,
                )
                if normalized_score < threshold:
                    logger.debug(
                        "[VectorService] Filtered out doc (score too low)"
                    )
                    continue
            content_key = doc.page_content.strip()
            if content_key in seen_content:
                continue
            seen_content.add(content_key)
            results.append(doc)

        logger.debug(
            "[VectorService] Returning %d documents after filtering",
            len(results),
        )

        return results

    def retrieve_scoped_content(
        self,
        syllabus_id: int,
        user_id: int,
        query_text: str,
        k: Optional[int] = None,
    ) -> str:
        """Retrieve relevant chunks for a given syllabus (scoped to its
        owner) and join them into a plain content string.

        Used by Quiz/Flashcard generation to pull content relevant to a
        specific subject/chapter instead of blindly truncating the first
        N characters of the whole syllabus. Returns "" if nothing relevant
        is found (caller should fall back to extracted_text in that case).
        """
        collection_name = self.collection_name_for_syllabus(syllabus_id)
        docs = self.retrieve_context(
            collection_name,
            query_text,
            k=k,
            filter={
                "$and": [
                    {"user_id": user_id},
                    {"syllabus_id": syllabus_id},
                ]
            },
        )
        if not docs:
            return ""
        return "\n\n".join(doc.page_content for doc in docs)

    @staticmethod
    def format_context(documents: List[Document]) -> str:
        """Format retrieved chunks into a clear, source-labeled context
        block for the LLM, instead of naively concatenating page_content.
        """
        if not documents:
            return ""

        blocks = []
        for i, doc in enumerate(documents, start=1):
            meta = doc.metadata or {}
            subject = meta.get("subject") or "Unknown"
            chapter = meta.get("chapter") or "Unknown"
            topic = meta.get("topic") or "Unknown"
            blocks.append(
                f"SOURCE {i}\n"
                f"Subject: {subject}\n"
                f"Chapter: {chapter}\n"
                f"Topic: {topic}\n"
                f"Content:\n{doc.page_content.strip()}"
            )
        return "\n\n".join(blocks)

    def delete_collection(self, collection_name: str):
        """Delete a collection."""
        import shutil
        collection_path = os.path.join(self.persist_directory, collection_name)
        if os.path.exists(collection_path):
            shutil.rmtree(collection_path)
        logger.info(f"Deleted collection: {collection_name}")