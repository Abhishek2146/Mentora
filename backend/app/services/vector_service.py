"""
Embedding and Vector Service
"""
import json
import os
import re
from typing import List, Optional, Dict, Any

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


from app.services.embedding_service import EmbeddingService
from app.services.syllabus_structure import format_retrieval_context


class VectorService:
    COLLECTION_METADATA = {"hnsw:space": "cosine"}

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
        return f"syllabus_{syllabus_id}_{tag}_{settings.RAG_INDEX_VERSION}"

    def _ensure_directory(self):
        os.makedirs(self.persist_directory, exist_ok=True)
    
    def get_collection(self, collection_name: str) -> Chroma:
        """Get an existing ChromaDB collection (or create it with the
        correct distance metric if it doesn't exist yet)."""
        vector_db = Chroma(
            embedding_function=self.embedding_service.embeddings,
            persist_directory=self.persist_directory,
            collection_name=collection_name,
            collection_metadata=self.COLLECTION_METADATA,
        )
        return vector_db  

    def add_documents(self, collection_name: str, documents: List[Document]) -> Chroma:
        """Add documents to an existing collection."""
        vector_db = self.get_collection(collection_name)
        vector_db.add_documents(documents)
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

        try:
            scored = vector_db.similarity_search_with_relevance_scores(
                query, k=top_k, filter=filter
            )
        except Exception as e:
            logger.error(
                f"RAG retrieval failed for collection '{collection_name}' "
                f"(query={query!r}): {e}"
            )
            return []

        top_score = scored[0][1] if scored else None
        logger.info(
            f"RAG retrieval: collection={collection_name} query={query!r} "
            f"raw_results={len(scored)} top_score={top_score}"
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
        logger.info(
            f"RAG retrieval: collection={collection_name} "
            f"after_threshold_and_dedup={len(results)} threshold={threshold}"
        )

        return results

    def retrieve_scoped_content(
        self,
        syllabus_id: int,
        user_id: int,
        query_text: str,
        k: Optional[int] = None,
        course_id: Optional[int] = None,
    ) -> str:
        """Retrieve relevant chunks for a given syllabus (scoped to its
        owner) and join them into a plain content string.

        Used by Quiz/Flashcard generation to pull content relevant to a
        specific subject/chapter instead of blindly truncating the first
        N characters of the whole syllabus. Returns "" if nothing relevant
        is found (caller should fall back to extracted_text in that case).
        """
        conditions: List[dict] = [
            {"user_id": user_id},
            {"syllabus_id": syllabus_id},
        ]
        if course_id is not None:
            # Kept for API compatibility; structured documents carry the
            # owning syllabus_id, which already scopes per course.
            pass
        metadata_filter = {"$and": conditions}

        collection_name = self.collection_name_for_syllabus(syllabus_id)
        logger.info(
            "[RETRIEVAL] syllabus_id=%s user_id=%s k=%s query=%r",
            syllabus_id, user_id, k, query_text[:120],
        )
        docs = self.retrieve_context(
            collection_name,
            query_text,
            k=k,
            filter=metadata_filter,
        )
        for doc in docs:
            meta = doc.metadata or {}
            logger.info(
                "[RETRIEVAL] hit: unit=%r topic=%r source=%s",
                meta.get("unit_title"),
                meta.get("topic_title"),
                meta.get("source"),
            )
        if not docs:
            return ""
        return "\n\n".join(doc.page_content for doc in docs)

    @staticmethod
    def format_context(documents: List[Document]) -> str:
        """Format retrieved chunks into a clear, source-labeled context
        block for the LLM, instead of naively concatenating page_content.
        """
        return format_retrieval_context(documents)

    def delete_collection(self, collection_name: str):
        """Delete a ChromaDB collection.

        Modern Chroma (>= 0.4) stores collections inside the shared
        ``chroma.sqlite3`` rather than as a directory named after the
        collection, so the delete must go through the Chroma client.
        Falls back to removing a legacy on-disk folder when the client
        delete is unavailable.
        """
        try:
            vector_db = self.get_collection(collection_name)
            vector_db.delete_collection()
            logger.info(f"Deleted collection: {collection_name}")
            return
        except Exception as e:
            logger.warning(
                "Client delete failed for collection '%s': %s",
                collection_name,
                e,
            )
        import shutil
        collection_path = os.path.join(self.persist_directory, collection_name)
        if os.path.exists(collection_path):
            shutil.rmtree(collection_path)
            logger.info(f"Deleted collection folder: {collection_name}")
