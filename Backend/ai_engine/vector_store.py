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
            # 回退：未安装 chromadb 时使用内存客户端
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
        将文档写入某个工作流的向量知识库。

        参数：
            workflow_id：目标工作流 ID。
            documents：LangChain Document 列表。
            metadata：可选元数据，会合并到每个 document.metadata 中。

        返回：
            chunk_id 列表（Chroma 的内部 ID）。
        """
        collection = self.get_collection(workflow_id)
        base_metadata = metadata or {}

        # 将基础 metadata 合并到每个文档
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
        在某个工作流的知识库上执行语义相似度检索。

        参数：
            workflow_id：目标工作流 ID。
            query：检索 query。
            top_k：返回条数（默认 5）。
            filter_dict：可选元数据过滤（例如 {"source": "manual.pdf"}）。

        返回：
            匹配的 LangChain Document 列表（按相关度排序）。
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
        带相关度分数的相似度检索。

        返回：
            (Document, score) 元组列表。score 越小表示越相似。
        """
        collection = self.get_collection(workflow_id)
        return collection.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=filter_dict,
        )

    def delete_collection(self, workflow_id: int) -> None:
        """
        删除某个工作流的全部知识库文档。

        参数：
            workflow_id：目标工作流 ID。
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
            pass  # 集合可能不存在

    def get_collection_stats(self, workflow_id: int) -> dict[str, Any]:
        """
        返回某个工作流向量集合的统计信息。

        返回：
            包含文档数量与向量维度等信息的字典。
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
        按 document_id 删除指定文档的分块（chunk）。

        参数：
            workflow_id：目标工作流 ID。
            document_id：要删除的文档 ID（匹配 metadata.document_id）。
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
        更新文档文本并重新向量化。

        说明：Chroma 不支持原地更新，因此采用“删除旧 chunk → 重新写入”的方式。

        参数：
            workflow_id：目标工作流 ID。
            document_id：要更新的文档 ID。
            new_text：新的文本内容。
        """
        collection = self.get_collection(workflow_id)

        # 查找已有分块
        existing = collection.get(filter={"document_id": document_id})
        if not existing or not existing.get("ids"):
            return

        # 删除旧分块
        collection.delete(ids=existing["ids"])

        # 用新文本重新写入
        old_docs = [
            Document(page_content=old_text, metadata=old_meta)
            for old_text, old_meta in zip(existing.get("documents", []), existing.get("metadatas", []))
        ]
        collection.add_documents(old_docs)

    # ─── Singleton Access ────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "VectorStoreManager":
        """获取单例 VectorStoreManager 实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_vector_store() -> VectorStoreManager:
    """便捷方法：获取单例实例。"""
    return VectorStoreManager.get_instance()
