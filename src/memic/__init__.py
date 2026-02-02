"""Memic Python SDK - File uploads and semantic search for context engineering."""

from ._version import __version__
from .client import Memic
from .exceptions import APIError, AuthenticationError, MemicError, NotFoundError
from .types import (
    File,
    FileStatus,
    MetadataFilters,
    PageRange,
    Project,
    SearchResult,
    SearchResults,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "Memic",
    # Types
    "File",
    "FileStatus",
    "MetadataFilters",
    "PageRange",
    "Project",
    "SearchResult",
    "SearchResults",
    # Exceptions
    "MemicError",
    "AuthenticationError",
    "NotFoundError",
    "APIError",
]
