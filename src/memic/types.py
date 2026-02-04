"""Type definitions for the Memic SDK using Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from pydantic import BaseModel, Field


class FileStatus(str, Enum):
    """File processing status enum."""

    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    UPLOAD_FAILED = "upload_failed"
    CONVERSION_STARTED = "conversion_started"
    CONVERSION_COMPLETE = "conversion_complete"
    CONVERSION_FAILED = "conversion_failed"
    PARSING_STARTED = "parsing_started"
    PARSING_COMPLETE = "parsing_complete"
    PARSING_FAILED = "parsing_failed"
    CHUNKING_STARTED = "chunking_started"
    CHUNKING_COMPLETE = "chunking_complete"
    CHUNKING_FAILED = "chunking_failed"
    EMBEDDING_STARTED = "embedding_started"
    EMBEDDING_COMPLETE = "embedding_complete"
    EMBEDDING_FAILED = "embedding_failed"
    READY = "ready"

    @property
    def is_failed(self) -> bool:
        """Check if status indicates a failure."""
        return self.value.endswith("_failed")

    @property
    def is_processing(self) -> bool:
        """Check if file is still being processed."""
        return not self.is_failed and self != FileStatus.READY


class Project(BaseModel):
    """Project information."""

    id: str
    name: str
    organization_id: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class File(BaseModel):
    """File information returned from the API."""

    id: str
    name: str
    original_filename: str
    size: int
    mime_type: str
    project_id: str
    status: FileStatus
    reference_id: Optional[str] = None
    error_message: Optional[str] = None
    total_chunks: int = 0
    total_embeddings: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PageRange(BaseModel):
    """Page range filter for search."""

    gte: Optional[int] = Field(None, description="Page number >= this value", ge=1)
    lte: Optional[int] = Field(None, description="Page number <= this value", ge=1)


class MetadataFilters(BaseModel):
    """Metadata filters for vector search.

    Used to filter search results by file reference, page number, category, etc.

    Example:
        # Filter by reference_id
        MetadataFilters(reference_id="TG_G1_Math")

        # Filter by reference_id and page range
        MetadataFilters(
            reference_id="TG_G1_Math",
            page_range=PageRange(gte=1, lte=50)
        )
    """

    reference_id: Optional[str] = Field(
        None, description="Filter by client-provided file reference ID"
    )
    reference_ids: Optional[List[str]] = Field(
        None, description="Filter by multiple reference IDs (OR logic)"
    )
    page_number: Optional[int] = Field(None, description="Filter by exact page number", ge=1)
    page_numbers: Optional[List[int]] = Field(
        None, description="Filter by multiple page numbers (OR logic)"
    )
    page_range: Optional[PageRange] = Field(None, description="Filter by page number range")
    category: Optional[str] = Field(None, description="Filter by category")
    document_type: Optional[str] = Field(None, description="Filter by document type")

    def to_api_format(self) -> Dict[str, Any]:
        """Convert to API request format."""
        result: Dict[str, Any] = {}

        if self.reference_id:
            result["reference_id"] = self.reference_id
        if self.reference_ids:
            result["reference_ids"] = self.reference_ids
        if self.page_number is not None:
            result["page_number"] = self.page_number
        if self.page_numbers:
            result["page_numbers"] = self.page_numbers
        if self.page_range:
            result["page_range"] = self.page_range.model_dump(exclude_none=True)
        if self.category:
            result["category"] = self.category
        if self.document_type:
            result["document_type"] = self.document_type

        return result


class ColumnInfo(BaseModel):
    """Column metadata for structured results."""

    name: str = Field(description="Column name")
    type: str = Field(description="Column data type (e.g., varchar, integer)")
    description: Optional[str] = Field(None, description="Human-readable column description")


class StructuredResult(BaseModel):
    """Structured query results with schema metadata."""

    columns: List[ColumnInfo] = Field(default_factory=list, description="Column metadata")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Result rows as key-value objects")

    def __len__(self) -> int:
        """Return number of rows."""
        return len(self.rows)

    def __iter__(self) -> Iterator[Dict[str, Any]]:  # type: ignore[override]
        """Allow iterating directly over rows."""
        return iter(self.rows)

    @property
    def has_data(self) -> bool:
        """Check if there are any rows."""
        return len(self.rows) > 0


class SearchRouting(BaseModel):
    """Routing information for hybrid search."""

    route: str = Field(description="Route taken: 'semantic', 'structured', or 'hybrid'")
    reasoning: Optional[str] = Field(None, description="Explanation of routing decision")
    connector_id: Optional[str] = Field(None, description="Database connector ID if structured")
    connector_name: Optional[str] = Field(None, description="Database connector name")
    sql_generated: Optional[str] = Field(None, description="Generated SQL query for structured search")
    sql_explanation: Optional[str] = Field(None, description="Explanation of the generated SQL")


class SearchResult(BaseModel):
    """Individual search result chunk."""

    chunk_id: str
    file_id: str
    file_name: str
    content: str
    score: float
    chunk_index: int = 0
    page_number: Optional[int] = None
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    project_id: Optional[str] = None
    reference_id: Optional[str] = None
    category: Optional[str] = None
    document_type: Optional[str] = None
    bounding_boxes: Optional[Dict[str, Any]] = None


class ResultsContainer(BaseModel):
    """Container for all result types (semantic and structured)."""

    semantic: List[SearchResult] = Field(default_factory=list, description="Semantic search results")
    structured: Optional[StructuredResult] = Field(None, description="Structured query results with schema")


class SearchResults(BaseModel):
    """Container for search results with metadata.

    Supports both semantic (document) and structured (database) results.

    Example:
        >>> results = client.search(query="revenue data", project_id="...")
        >>> # Check routing
        >>> if results.routing:
        ...     print(f"Routed to: {results.routing.route}")
        >>> # Document results
        >>> for r in results.results.semantic:
        ...     print(f"[{r.score:.2f}] {r.file_name}: {r.content[:100]}")
        >>> # Database results
        >>> if results.results.structured:
        ...     for row in results.results.structured.rows:
        ...         print(f"Row: {row}")
    """

    model_config = {"arbitrary_types_allowed": True}

    query: str
    results: ResultsContainer = Field(default_factory=ResultsContainer)
    routing: Optional[SearchRouting] = None
    total_results: int = 0
    search_time_ms: float = 0.0

    def __iter__(self) -> Iterator[SearchResult]:  # type: ignore[override]
        """Allow iterating directly over semantic results for convenience."""
        return iter(self.results.semantic)

    def __len__(self) -> int:
        """Return number of semantic results."""
        return len(self.results.semantic)

    def __getitem__(self, index: int) -> SearchResult:
        """Allow indexing into semantic results."""
        return self.results.semantic[index]

    @property
    def semantic(self) -> List[SearchResult]:
        """Shortcut to access semantic results."""
        return self.results.semantic

    @property
    def structured(self) -> Optional[StructuredResult]:
        """Shortcut to access structured results."""
        return self.results.structured

    @property
    def has_structured(self) -> bool:
        """Check if results include structured/database data."""
        return self.results.structured is not None and self.results.structured.has_data

    @property
    def has_documents(self) -> bool:
        """Check if results include document data."""
        return len(self.results.semantic) > 0
