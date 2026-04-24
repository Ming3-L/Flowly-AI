"""
Vector Store Manager — Phase 8: RAG (Retrieval-Augmented Generation)

Manages Chroma vector collections per workflow for semantic document retrieval.
Each workflow gets its own collection, enabling isolated knowledge bases.

Features:
- Per-workflow collection isolation
- OpenAI text-embedding-3-small embeddings (configurable)
- Async add/search/delete operations
- Collection metadata tracking
"""

from __future__ import annotations

import os
from typing import Any, Optional

from langchain_chroma import Chroma  # pyright: ignore[reportMissingImports]
from langchain_openai import OpenAIEmbeddings  # pyright: ignore[reportMissingImports]
from langchain_core.documents import Document  # pyright: ignore[reportMissingImports]


class VectorStoreManager:
    """
    Central manager for workflow-level vector stores backed by Chroma.

    Each workflow maps to one Chroma collection named `workflow_{id}`.
    Collections are created lazily on first access.
    """

    _instance: Optional["VectorStoreManager"] = None

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        self.persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIR", "/data/chroma"
        )
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self._embeddings: Optional[OpenAIEmbeddings] = None
        self._collections: dict[str, Chroma] = {}

    @property
    def embeddings(self) -> OpenAIEmbeddings:
        """Lazily create the OpenAI-compatible embeddings client（密钥与 base 与豆包/方舟对齐）。"""
        if self._embeddings is None:
            from ai_engine.integrations import get_ai_provider_settings

            s = get_ai_provider_settings()
            api_key = s.language.doubao_ark_api_key or s.language.openai_api_key
            base_url = (
                s.language.doubao_ark_base_url
                if s.language.doubao_ark_api_key
                else s.language.openai_base_url
            )
            self._embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                api_key=api_key or None,
                base_url=base_url or None,
            )
        return self._embeddings

    def _collection_name(self, workflow_id: int) -> str:
        """Generate a safe collection name for a workflow."""
        return f"workflow_{workflow_id}"

    def get_collection(self, workflow_id: int) -> Chroma:
        """
        Get or create the Chroma collection for a workflow.

        Args:
            workflow_id: The ID of the workflow whose collection to access.

        Returns:
            A Chroma vector store instance for the workflow.
        """
        name = self._collection_name(workflow_id)
        if name not in self._collections:
            self._collections[name] = Chroma(
                client=self._get_chroma_client(),
                collection_name=name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
        return self._collections[name]

    def _get_chroma_client(self):
        """Build a Chroma persistence client."""
        try:
            import chromadb
            from chromadb.config import Settings

            return chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )
        except ImportError:
            # Fallback: in-memory if chromadb not installed
            import chromadb

            return chromadb.Client()

    # ─── Document Operations ──────────────────────────────────────────────────

    def add_documents(
        self,
        workflow_id: int,
        documents: list[Document],
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        """
        Add documents to a workflow's vector store.

        Args:
            workflow_id: Target workflow ID.
            documents: List of LangChain Document objects.
            metadata: Optional metadata dict merged into each document's metadata.

        Returns:
            List of chunk IDs (Chroma's internal IDs).
        """
        collection = self.get_collection(workflow_id)
        base_metadata = metadata or {}

        # Merge base metadata into each document
        enriched_docs = []
        for doc in documents:
            enriched_docs.append(
                Document(
                    page_content=doc.page_content,
                    metadata={**base_metadata, **doc.metadata},
                )
            )

        return collection.add_documents(enriched_docs)

    def similarity_search(
        self,
        workflow_id: int,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[dict[str, Any]] = None,
    ) -> list[Document]:
        """
        Perform semantic similarity search against a workflow's knowledge base.

        Args:
            workflow_id: Target workflow ID.
            query: The search query string.
            top_k: Number of results to return (default 5).
            filter_dict: Optional metadata filter (e.g. {"source": "manual.pdf"}).

        Returns:
            List of matching LangChain Document objects, ordered by relevance.
        """
        collection = self.get_collection(workflow_id)
        return collection.similarity_search(
            query=query,
            k=top_k,
            filter=filter_dict,
        )

    def similarity_search_with_score(
        self,
        workflow_id: int,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[dict[str, Any]] = None,
    ) -> list[tuple[Document, float]]:
        """
        Similarity search with relevance scores.

        Returns:
            List of (Document, score) tuples. Lower scores = more similar.
        """
        collection = self.get_collection(workflow_id)
        return collection.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=filter_dict,
        )

    def delete_collection(self, workflow_id: int) -> None:
        """
        Delete all documents for a workflow.

        Args:
            workflow_id: Target workflow ID.
        """
        name = self._collection_name(workflow_id)
        if name in self._collections:
            del self._collections[name]

        try:
            collection = Chroma(
                client=self._get_chroma_client(),
                collection_name=name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
            collection.delete_collection()
        except Exception:
            pass  # Collection may not exist

    def get_collection_stats(self, workflow_id: int) -> dict[str, Any]:
        """
        Return statistics for a workflow's vector collection.

        Returns:
            Dict with document count and embedding dimension.
        """
        collection = self.get_collection(workflow_id)
        try:
            count = collection._collection.count()
        except Exception:
            count = 0

        return {
            "workflow_id": workflow_id,
            "collection_name": self._collection_name(workflow_id),
            "document_count": count,
            "embedding_model": self.embedding_model,
            "persist_directory": self.persist_directory,
        }

    # ─── Batch Operations ────────────────────────────────────────────────────

    def delete_by_document_id(
        self, workflow_id: int, document_id: str
    ) -> None:
        """
        Delete specific document chunks by their IDs.

        Args:
            workflow_id: Target workflow ID.
            document_id: The document ID to delete (matches metadata.document_id).
        """
        collection = self.get_collection(workflow_id)
        collection.delete(filter={"document_id": document_id})

    def update_document(
        self,
        workflow_id: int,
        document_id: str,
        new_text: str,
    ) -> None:
        """
        Update a document's text and re-embed it.

        Note: Chroma doesn't support in-place updates, so we delete and re-add.

        Args:
            workflow_id: Target workflow ID.
            document_id: The document ID to update.
            new_text: The new text content.
        """
        collection = self.get_collection(workflow_id)

        # Find existing chunks
        existing = collection.get(filter={"document_id": document_id})
        if not existing or not existing.get("ids"):
            return

        # Delete old chunks
        collection.delete(ids=existing["ids"])

        # Re-add with new text
        old_docs = [
            Document(page_content=old_text, metadata=old_meta)
            for old_text, old_meta in zip(existing.get("documents", []), existing.get("metadatas", []))
        ]
        collection.add_documents(old_docs)

    # ─── Singleton Access ────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "VectorStoreManager":
        """Get the singleton VectorStoreManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_vector_store() -> VectorStoreManager:
    """Convenience alias for getting the singleton instance."""
    return VectorStoreManager.get_instance()
