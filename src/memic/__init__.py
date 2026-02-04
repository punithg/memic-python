"""Memic Python SDK - File uploads and semantic search for context engineering."""

from ._version import __version__
from .client import Memic
from .exceptions import APIError, AuthenticationError, MemicError, NotFoundError
from .types import (
    ColumnInfo,
    File,
    FileStatus,
    MetadataFilters,
    PageRange,
    Project,
    ResultsContainer,
    SearchResult,
    SearchResults,
    SearchRouting,
    StructuredResult,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "Memic",
    # Types
    "ColumnInfo",
    "File",
    "FileStatus",
    "MetadataFilters",
    "PageRange",
    "Project",
    "ResultsContainer",
    "SearchResult",
    "SearchResults",
    "SearchRouting",
    "StructuredResult",
    # Exceptions
    "MemicError",
    "AuthenticationError",
    "NotFoundError",
    "APIError",
]
