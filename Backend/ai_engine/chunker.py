"""
Smart Chunker — Phase 8: RAG

Intelligent text chunking with overlap for optimal embedding quality.
Supports semantic chunking, structured document awareness, and source tracking.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from langchain_core.documents import Document  # pyright: ignore[reportMissingImports]
from langchain_text_splitters import RecursiveCharacterTextSplitter  # pyright: ignore[reportMissingImports]


class SmartChunker:
    """
    Configurable text chunking optimized for RAG retrieval quality.

    Default config targets ~1000 tokens per chunk with 200 token overlap,
    prioritizing paragraph boundaries to preserve semantic coherence.
    """

    DEFAULT_CONFIG: dict[str, Any] = {
        "chunk_size": 1000,          # Target chars per chunk (~250 tokens)
        "chunk_overlap": 200,        # Overlap between chunks
        "separators": [
            "\n\n",      # Paragraph break — highest priority
            "\n",        # Line break
            "。",        # Chinese sentence
            "？",        # Chinese question
            "！",        # Chinese exclamation
            ". ",        # English sentence
            "? ",        # English question
            "! ",        # English exclamation
            "; ",        # Clause separator
            ", ",        # Comma clause
            " ",         # Word boundary
            "",          # Character fallback
        ],
        "keep_separator": True,
        "add_start_index": True,
    }

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._splitter: Optional[RecursiveCharacterTextSplitter] = None

    @property
    def splitter(self) -> RecursiveCharacterTextSplitter:
        """Lazily build the RecursiveCharacterTextSplitter instance."""
        if self._splitter is None:
            self._splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config["chunk_size"],
                chunk_overlap=self.config["chunk_overlap"],
                separators=self.config["separators"],
                keep_separator=self.config["keep_separator"],
                add_start_index=self.config["add_start_index"],
            )
        return self._splitter

    def chunk(
        self,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Document]:
        """
        Split a document into semantically coherent chunks.

        Args:
            text: The full text content to chunk.
            metadata: Metadata dict attached to every chunk.

        Returns:
            List of LangChain Document chunks, each with:
            - page_content: the chunk text
            - metadata: base metadata + chunk index info
        """
        if not text.strip():
            return []

        base_meta = metadata or {}

        raw_chunks = self.splitter.split_text(text)
        documents: list[Document] = []

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_meta = {
                **base_meta,
                "chunk_index": idx,
                "total_chunks": len(raw_chunks),
                "chunk_size_chars": len(chunk_text),
            }
            documents.append(Document(page_content=chunk_text, metadata=chunk_meta))

        return documents

    def chunk_document(
        self,
        document: Document,
    ) -> list[Document]:
        """
        Chunk a LangChain Document while preserving its metadata.

        Args:
            document: A LangChain Document with existing metadata.

        Returns:
            List of chunk Documents, each inheriting the original metadata
            plus chunk index information.
        """
        return self.chunk(document.page_content, metadata=document.metadata)

    def chunk_with_page_tracking(
        self,
        pages: list[dict[str, Any]],
        source_metadata: Optional[dict[str, Any]] = None,
    ) -> list[Document]:
        """
        Chunk text organized by pages while tracking page numbers.

        Args:
            pages: List of dicts with keys "page_number" (1-indexed) and "text".
            source_metadata: Additional metadata for all chunks.

        Returns:
            List of chunk Documents with page tracking in metadata.
        """
        documents: list[Document] = []
        base_meta = source_metadata or {}

        for page in pages:
            page_num = page.get("page_number", 1)
            page_text = page.get("text", "").strip()
            if not page_text:
                continue

            page_chunks = self.chunk(
                page_text,
                metadata={
                    **base_meta,
                    "source_type": "page",
                    "page_number": page_num,
                },
            )

            # Update page_number in each chunk's metadata
            for chunk in page_chunks:
                chunk.metadata["page_number"] = page_num

            documents.extend(page_chunks)

        return documents

    def preview(
        self,
        text: str,
        num_preview_chunks: int = 3,
    ) -> dict[str, Any]:
        """
        Preview chunking results without creating full Document list.

        Useful for showing users how their document will be split before committing.

        Args:
            text: The text to preview.
            num_preview_chunks: How many chunks to return in the preview.

        Returns:
            Dict with preview chunks, statistics, and config used.
        """
        if not text.strip():
            return {
                "chunks": [],
                "total_chunks": 0,
                "config": self.config,
                "avg_chunk_size_chars": 0,
            }

        raw_chunks = self.splitter.split_text(text)
        preview = raw_chunks[:num_preview_chunks]
        total_chars = sum(len(c) for c in raw_chunks)

        return {
            "chunks": [
                {
                    "index": idx,
                    "text": chunk,
                    "char_count": len(chunk),
                    "word_count": len(chunk.split()),
                }
                for idx, chunk in enumerate(preview)
            ],
            "total_chunks": len(raw_chunks),
            "config": self.config,
            "avg_chunk_size_chars": total_chars // max(len(raw_chunks), 1),
            "has_more": len(raw_chunks) > num_preview_chunks,
            "remaining_count": len(raw_chunks) - num_preview_chunks,
        }


# Convenience singleton
_default_chunker: Optional[SmartChunker] = None


def get_default_chunker() -> SmartChunker:
    """Get the default SmartChunker instance."""
    global _default_chunker
    if _default_chunker is None:
        _default_chunker = SmartChunker()
    return _default_chunker


def chunk_document(document: Document) -> list[Document]:
    """Quick helper: chunk a document using the default chunker."""
    return get_default_chunker().chunk_document(document)
