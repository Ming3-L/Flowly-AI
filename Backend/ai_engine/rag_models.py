"""
Document Model — Phase 8: RAG

Django model for storing knowledge base documents with processing status tracking.
"""

from django.contrib.auth.models import User
from django.db import models


class Document(models.Model):
    """
    Represents a document uploaded to a workflow's knowledge base.

    Tracks processing status from upload → chunking → embedding → ready.
    """

    PROCESSING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("chunking", "Chunking"),
        ("embedding", "Embedding"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    EMBEDDING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
    ]

    workflow = models.ForeignKey(
        "ai_engine.Workflow",
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="Workflow this document belongs to",
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flowly_documents",
        help_text="User who uploaded this document",
    )

    # File information
    filename = models.CharField(max_length=255, help_text="Original filename")
    file_type = models.CharField(
        max_length=50,
        help_text="File type: pdf, docx, txt, html, md, csv",
    )
    file_size = models.BigIntegerField(help_text="File size in bytes")
    file_path = models.CharField(
        max_length=512,
        help_text="Storage path of the uploaded file",
    )

    # Processing status
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="pending",
    )
    processing_error = models.TextField(
        blank=True,
        default="",
        help_text="Error message if processing failed",
    )

    # Chunking and embedding
    chunk_count = models.IntegerField(
        default=0,
        help_text="Number of chunks created from this document",
    )
    embedding_status = models.CharField(
        max_length=20,
        choices=EMBEDDING_STATUS_CHOICES,
        default="pending",
    )

    # Document metadata
    title = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Document title (extracted from metadata)",
    )
    author = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Document author",
    )
    total_pages = models.IntegerField(
        default=0,
        help_text="Total pages (for PDFs)",
    )
    document_metadata = models.JSONField(
        default=dict,
        help_text="Additional document metadata (JSON)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Knowledge Base Document"
        verbose_name_plural = "Knowledge Base Documents"
        indexes = [
            models.Index(fields=["workflow", "processing_status"]),
            models.Index(fields=["workflow", "embedding_status"]),
        ]

    def __str__(self):
        return f"{self.filename} ({self.workflow.name})"

    @property
    def is_ready(self) -> bool:
        """True if document is fully processed and embedded."""
        return (
            self.processing_status == "completed"
            and self.embedding_status == "completed"
            and self.chunk_count > 0
        )

    @property
    def is_processing(self) -> bool:
        """True if document is currently being processed."""
        return self.processing_status in ("pending", "chunking", "embedding")
