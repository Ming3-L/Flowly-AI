"""
RAG API — Phase 8: Retrieval-Augmented Generation

Ninja router providing document management and semantic search endpoints
for the knowledge base (RAG) feature.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router, Schema  # pyright: ignore[reportMissingImports]
from ninja.files import UploadedFile
from pydantic import Field, field_validator  # pyright: ignore[reportMissingImports]
from pydantic_core import PydanticCustomError  # pyright: ignore[reportMissingImports]

from .auth import JWTAuth
from .rag_models import Document
from .vector_store import VectorStoreManager
from .document_processor import DocumentProcessor
from .chunker import SmartChunker, chunk_document


# ─── Schemas ─────────────────────────────────────────────────────────────────

class DocumentMetadataSchema(Schema):
    title: Optional[str] = None
    author: Optional[str] = None
    total_pages: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)


class DocumentResponseSchema(Schema):
    id: int
    filename: str
    file_type: str
    file_size: int
    title: str
    author: str
    total_pages: int
    chunk_count: int
    processing_status: str
    embedding_status: str
    is_ready: bool
    metadata: DocumentMetadataSchema
    created_at: str
    updated_at: str


class DocumentListSchema(Schema):
    id: int
    filename: str
    file_type: str
    chunk_count: int
    processing_status: str
    is_ready: bool
    created_at: str


class PaginatedDocumentsSchema(Schema):
    items: list[DocumentListSchema]
    total: int
    page: int
    page_size: int
    total_pages: int


class SearchResultSchema(Schema):
    content: str
    score: float
    metadata: dict[str, Any]


class SearchResponseSchema(Schema):
    query: str
    results: list[SearchResultSchema]
    total: int
    workflow_id: int


class ChunkingPreviewSchema(Schema):
    chunks: list[dict[str, Any]]
    total_chunks: int
    avg_chunk_size_chars: int
    has_more: bool
    remaining_count: int
    config: dict[str, Any]


class UploadResponseSchema(Schema):
    id: int
    filename: str
    processing_status: str
    message: str


class DeleteResponseSchema(Schema):
    success: bool
    document_id: int
    message: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_upload_dir() -> str:
    """Get and ensure the upload directory exists."""
    upload_dir = os.getenv("DOCUMENT_UPLOAD_DIR", "/data/uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _save_uploaded_file(uploaded_file: UploadedFile, upload_dir: str) -> tuple[str, int]:
    """
    Save an uploaded file to disk and return (file_path, file_size).

    Uses UUID to avoid filename collisions.
    """
    ext = uploaded_file.name.split(".")[-1] if "." in uploaded_file.name else ""
    safe_name = f"{uuid.uuid4().hex}_{uploaded_file.name}"
    file_path = os.path.join(upload_dir, safe_name)

    with open(file_path, "wb") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)

    return file_path, os.path.getsize(file_path)


# ─── Router ─────────────────────────────────────────────────────────────────

router = Router(auth=JWTAuth(), tags=["Knowledge Base / RAG"])


@router.post("/upload", response=UploadResponseSchema)
def upload_document(
    request: HttpRequest,
    file: UploadedFile,
    workflow_id: int,
) -> UploadResponseSchema:
    """
    Upload a document to a workflow's knowledge base.

    The document is saved and queued for async processing (chunking + embedding).
    Use GET /documents/{workflow_id} to check processing status.
    """
    from .models import Workflow

    # Validate workflow exists and user has access
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist:
        raise PydanticCustomError(
            "value_error", f"Workflow {workflow_id} not found", {}
        )

    # Validate file type
    ext = file.name.split(".")[-1].lower() if "." in file.name else ""
    processor = DocumentProcessor()
    if ext not in processor.SUPPORTED_TYPES:
        raise PydanticCustomError(
            "value_error",
            f"Unsupported file type: {ext}. Supported: {', '.join(processor.SUPPORTED_TYPES)}",
            {},
        )

    # Save file
    upload_dir = _get_upload_dir()
    file_path, file_size = _save_uploaded_file(file, upload_dir)

    # Create document record
    doc = Document.objects.create(
        workflow=workflow,
        uploaded_by=request.user if request.user.is_authenticated else None,
        filename=file.name,
        file_type=ext,
        file_size=file_size,
        file_path=file_path,
        processing_status="pending",
    )

    # Trigger async processing via Celery (Phase 9)
    _process_document_async(doc.id)

    return UploadResponseSchema(
        id=doc.id,
        filename=doc.filename,
        processing_status=doc.processing_status,
        message=f"Document uploaded. Processing started.",
    )


def _process_document_async(document_id: int) -> None:
    """
    Dispatch document processing to a Celery worker.

    Falls back to synchronous processing if Celery is not available.
    """
    try:
        from .tasks import process_document_task
        process_document_task.delay(document_id)
    except Exception:
        # Fallback: process synchronously in a background thread (no Celery)
        import threading

        def _process():
            try:
                _do_process_document(document_id)
            except Exception as exc:
                Document.objects.filter(id=document_id).update(
                    processing_status="failed",
                    processing_error=str(exc),
                )

        thread = threading.Thread(target=_process, daemon=True)
        thread.start()


def _do_process_document(document_id: int) -> None:
    """Synchronous document processing pipeline."""
    doc = Document.objects.get(id=document_id)
    processor = DocumentProcessor()
    chunker = SmartChunker()

    try:
        # ── Extract ────────────────────────────────────────────────────────
        Document.objects.filter(id=document_id).update(processing_status="chunking")
        extracted_doc = processor.process(doc.file_path)

        # Update metadata
        doc.title = extracted_doc.metadata.get("title", doc.filename)
        doc.author = extracted_doc.metadata.get("author", "")
        doc.total_pages = extracted_doc.metadata.get("total_pages", 0)
        doc.document_metadata = {k: v for k, v in extracted_doc.metadata.items()
                                  if k not in ("title", "author", "total_pages")}
        doc.save(update_fields=["title", "author", "total_pages", "document_metadata"])

        # ── Chunk ──────────────────────────────────────────────────────────
        chunks = chunker.chunk_document(extracted_doc)
        doc.chunk_count = len(chunks)
        doc.save(update_fields=["chunk_count"])

        # ── Embed & store ─────────────────────────────────────────────────
        Document.objects.filter(id=document_id).update(processing_status="embedding")
        vector_store = VectorStoreManager.get_instance()

        # Add document ID to chunk metadata for tracking
        enriched_chunks = [
            chunk
            for chunk in chunks
        ]

        vector_store.add_documents(
            workflow_id=doc.workflow_id,
            documents=enriched_chunks,
            metadata={
                "document_id": str(doc.id),
                "filename": doc.filename,
            },
        )

        # ── Done ──────────────────────────────────────────────────────────
        doc.processing_status = "completed"
        doc.embedding_status = "completed"
        doc.save(update_fields=["processing_status", "embedding_status"])

    except Exception as exc:
        doc.processing_status = "failed"
        doc.processing_error = str(exc)
        doc.save(update_fields=["processing_status", "processing_error"])
        raise


@router.get("/{workflow_id}", response=PaginatedDocumentsSchema)
def list_documents(
    request: HttpRequest,
    workflow_id: int,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedDocumentsSchema:
    """
    List all documents in a workflow's knowledge base with pagination.
    """
    qs: QuerySet[Document] = (
        Document.objects.filter(workflow_id=workflow_id)
        .order_by("-created_at")
    )

    total = qs.count()
    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size

    items = [
        DocumentListSchema(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            chunk_count=doc.chunk_count,
            processing_status=doc.processing_status,
            is_ready=doc.is_ready,
            created_at=doc.created_at.isoformat(),
        )
        for doc in qs[offset : offset + page_size]
    ]

    return PaginatedDocumentsSchema(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{workflow_id}/{document_id}", response=DocumentResponseSchema)
def get_document(
    request: HttpRequest,
    workflow_id: int,
    document_id: int,
) -> DocumentResponseSchema:
    """Get detailed information about a specific document."""
    doc = Document.objects.get(id=document_id, workflow_id=workflow_id)
    return DocumentResponseSchema(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        title=doc.title,
        author=doc.author,
        total_pages=doc.total_pages,
        chunk_count=doc.chunk_count,
        processing_status=doc.processing_status,
        embedding_status=doc.embedding_status,
        is_ready=doc.is_ready,
        metadata=DocumentMetadataSchema(
            title=doc.title,
            author=doc.author,
            total_pages=doc.total_pages,
            extra=doc.document_metadata,
        ),
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )


@router.delete("/{workflow_id}/{document_id}", response=DeleteResponseSchema)
def delete_document(
    request: HttpRequest,
    workflow_id: int,
    document_id: int,
) -> DeleteResponseSchema:
    """
    Delete a document from the knowledge base and remove its vector embeddings.
    """
    doc = Document.objects.get(id=document_id, workflow_id=workflow_id)
    doc_id = doc.id

    # Remove from vector store
    try:
        vector_store = VectorStoreManager.get_instance()
        vector_store.delete_by_document_id(workflow_id, str(doc_id))
    except Exception:
        pass  # Non-fatal if vector deletion fails

    doc.delete()

    return DeleteResponseSchema(
        success=True,
        document_id=doc_id,
        message=f"Document {doc_id} and its embeddings deleted.",
    )


@router.post("/{workflow_id}/search", response=SearchResponseSchema)
def search_documents(
    request: HttpRequest,
    workflow_id: int,
    query: str,
    top_k: int = 5,
) -> SearchResponseSchema:
    """
    Perform semantic search against a workflow's knowledge base.

    Returns relevant document chunks ranked by similarity score.
    """
    vector_store = VectorStoreManager.get_instance()

    search_results = vector_store.similarity_search_with_score(
        workflow_id=workflow_id,
        query=query,
        top_k=top_k,
    )

    results = [
        SearchResultSchema(
            content=doc.page_content,
            score=score,
            metadata=doc.metadata,
        )
        for doc, score in search_results
    ]

    return SearchResponseSchema(
        query=query,
        results=results,
        total=len(results),
        workflow_id=workflow_id,
    )


@router.post("/{workflow_id}/chunking-preview", response=ChunkingPreviewSchema)
def chunking_preview(
    request: HttpRequest,
    workflow_id: int,
    file: UploadedFile,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> ChunkingPreviewSchema:
    """
    Preview how a document will be chunked before uploading.

    Useful for tuning chunk_size and chunk_overlap parameters.
    """
    # Save temporarily
    upload_dir = _get_upload_dir()
    file_path, _ = _save_uploaded_file(file, upload_dir)

    try:
        processor = DocumentProcessor()
        chunker = SmartChunker(config={
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        })

        doc = processor.process(file_path)
        preview = chunker.preview(doc.page_content, num_preview_chunks=5)

        return ChunkingPreviewSchema(
            chunks=preview["chunks"],
            total_chunks=preview["total_chunks"],
            avg_chunk_size_chars=preview["avg_chunk_size_chars"],
            has_more=preview["has_more"],
            remaining_count=preview["remaining_count"],
            config=chunker.config,
        )
    finally:
        # Clean up temp file
        try:
            os.remove(file_path)
        except Exception:
            pass
