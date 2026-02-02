"""Main Memic client for interacting with the API."""

import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from ._version import __version__
from .exceptions import APIError, AuthenticationError, MemicError, NotFoundError
from .types import File, FileStatus, MetadataFilters, Project, SearchResult, SearchResults


class Memic:
    """Memic SDK client for file uploads and semantic search.

    Example:
        >>> from memic import Memic, MetadataFilters
        >>>
        >>> client = Memic(api_key="mk_...")  # or use MEMIC_API_KEY env var
        >>>
        >>> # Upload a file
        >>> file = client.upload_file(
        ...     project_id="...",
        ...     file_path="/path/to/doc.pdf",
        ... )
        >>>
        >>> # Search with filters
        >>> results = client.search(
        ...     query="key findings",
        ...     project_id="...",
        ...     filters=MetadataFilters(reference_id="TG_G1_Math")
        ... )
    """

    DEFAULT_BASE_URL = "https://app.memic.ai"
    DEFAULT_TIMEOUT = 30
    DEFAULT_POLL_INTERVAL = 2.0
    DEFAULT_POLL_TIMEOUT = 300

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the Memic client.

        Args:
            api_key: Memic API key. If not provided, reads from MEMIC_API_KEY env var.
            base_url: Override the API base URL (for development/testing).
            timeout: Request timeout in seconds (default: 30).

        Raises:
            AuthenticationError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("MEMIC_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "No API key provided. Pass api_key parameter or set MEMIC_API_KEY env var."
            )

        self.base_url = (base_url or os.environ.get("MEMIC_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._org_id: Optional[str] = None

        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": f"memic-python/{__version__}",
            "Content-Type": "application/json",
        })

    @property
    def org_id(self) -> str:
        """Get organization ID (fetched from API key on first access)."""
        if self._org_id is None:
            self._org_id = self._fetch_org_id()
        return self._org_id

    def _fetch_org_id(self) -> str:
        """Fetch organization ID from the API key."""
        response = self._request("GET", "/api-keys/me")
        return str(response["organization_id"])

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API path (will be prefixed with base_url).
            json: JSON body for POST/PUT requests.
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            AuthenticationError: For 401/403 responses.
            NotFoundError: For 404 responses.
            APIError: For other error responses.
        """
        url = f"{self.base_url}{path}"

        try:
            response = self._session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise APIError(f"Request failed: {e}")

        if response.status_code == 401 or response.status_code == 403:
            raise AuthenticationError(self._get_error_message(response))
        elif response.status_code == 404:
            raise NotFoundError(self._get_error_message(response))
        elif response.status_code >= 400:
            raise APIError(
                self._get_error_message(response),
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code == 204:
            return {}

        result: Dict[str, Any] = response.json()
        return result

    def _get_error_message(self, response: requests.Response) -> str:
        """Extract error message from response."""
        try:
            data: Dict[str, Any] = response.json()
            detail = data.get("detail")
            if detail is not None:
                return str(detail)
            message = data.get("message")
            if message is not None:
                return str(message)
            return response.text or f"HTTP {response.status_code}"
        except Exception:
            return response.text or f"HTTP {response.status_code}"

    def list_projects(self) -> List[Project]:
        """List all projects in the organization.

        Returns:
            List of Project objects.

        Example:
            >>> projects = client.list_projects()
            >>> for p in projects:
            ...     print(f"{p.name}: {p.id}")
        """
        response = self._request("GET", f"/organizations/{self.org_id}/projects/")
        if isinstance(response, list):
            return [Project(**p) for p in response]
        return []

    def upload_file(
        self,
        project_id: str,
        file_path: Union[str, Path],
        wait_for_ready: bool = True,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
    ) -> File:
        """Upload a file to a project.

        Uses the 3-step presigned URL flow:
        1. Initialize upload to get presigned URL
        2. PUT file directly to storage
        3. Confirm upload to trigger processing

        Args:
            project_id: Target project ID.
            file_path: Path to the file to upload.
            wait_for_ready: If True, poll until file is READY (default: True).
            reference_id: Optional reference ID for external system linking.
            metadata: Optional metadata key-value pairs.
            poll_interval: Seconds between status polls (default: 2.0).
            poll_timeout: Max seconds to wait for READY status (default: 300).

        Returns:
            File object with current status.

        Raises:
            FileNotFoundError: If file_path doesn't exist.
            MemicError: If file processing fails.

        Example:
            >>> file = client.upload_file(
            ...     project_id="...",
            ...     file_path="/path/to/doc.pdf",
            ...     reference_id="lesson_123"
            ... )
            >>> print(f"Uploaded: {file.id}, status: {file.status}")
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file info
        file_size = file_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        # Step 1: Initialize upload
        init_payload: Dict[str, Any] = {
            "filename": file_path.name,
            "size": file_size,
            "mime_type": mime_type,
        }
        if reference_id:
            init_payload["reference_id"] = reference_id
        if metadata:
            init_payload["metadata"] = metadata

        init_response = self._request(
            "POST",
            f"/projects/{project_id}/files/init",
            json=init_payload,
        )

        file_id = init_response["file_id"]
        upload_url = init_response["upload_url"]

        # Step 2: PUT file to presigned URL
        with open(file_path, "rb") as f:
            put_response = requests.put(
                upload_url,
                data=f,
                headers={"Content-Type": mime_type},
                timeout=self.timeout * 10,  # Longer timeout for uploads
            )
            if put_response.status_code >= 400:
                raise APIError(
                    f"Failed to upload file to storage: {put_response.text}",
                    status_code=put_response.status_code,
                )

        # Step 3: Confirm upload
        confirm_response = self._request(
            "POST",
            f"/projects/{project_id}/files/{file_id}/confirm",
        )

        file = File(**self._normalize_file_response(confirm_response))

        # Wait for ready if requested
        if wait_for_ready:
            file = self.wait_for_ready(
                project_id=project_id,
                file_id=file.id,
                poll_interval=poll_interval,
                poll_timeout=poll_timeout,
            )

        return file

    def get_file_status(self, project_id: str, file_id: str) -> File:
        """Get the current status of a file.

        Args:
            project_id: Project ID containing the file.
            file_id: File ID to check.

        Returns:
            File object with current status.

        Example:
            >>> file = client.get_file_status(project_id, file_id)
            >>> print(f"Status: {file.status}, is_processing: {file.status.is_processing}")
        """
        response = self._request(
            "GET",
            f"/projects/{project_id}/files/{file_id}/status",
        )
        return File(**self._normalize_file_response(response))

    def wait_for_ready(
        self,
        project_id: str,
        file_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
    ) -> File:
        """Wait for a file to reach READY status.

        Args:
            project_id: Project ID containing the file.
            file_id: File ID to wait for.
            poll_interval: Seconds between status checks (default: 2.0).
            poll_timeout: Max seconds to wait (default: 300).

        Returns:
            File object with READY status.

        Raises:
            MemicError: If file processing fails or timeout is reached.
        """
        start_time = time.time()

        while True:
            file = self.get_file_status(project_id, file_id)

            if file.status == FileStatus.READY:
                return file

            if file.status.is_failed:
                raise MemicError(
                    f"File processing failed with status {file.status.value}: "
                    f"{file.error_message or 'Unknown error'}"
                )

            elapsed = time.time() - start_time
            if elapsed >= poll_timeout:
                raise MemicError(
                    f"Timeout waiting for file to be ready. "
                    f"Current status: {file.status.value}"
                )

            time.sleep(poll_interval)

    def search(
        self,
        query: str,
        project_id: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        top_k: int = 10,
        min_score: float = 0.7,
        filters: Optional[MetadataFilters] = None,
    ) -> SearchResults:
        """Search for content across documents.

        Args:
            query: Search query text.
            project_id: Optional project ID to limit search scope.
            file_ids: Optional list of file IDs to search within.
            top_k: Number of results to return (default: 10, max: 50).
            min_score: Minimum similarity score threshold (default: 0.7).
            filters: Optional metadata filters (reference_id, page_number, etc.).

        Returns:
            SearchResults object containing matching chunks.

        Example:
            >>> results = client.search(
            ...     query="key findings",
            ...     project_id="...",
            ...     filters=MetadataFilters(
            ...         reference_id="TG_G1_Math",
            ...         page_range=PageRange(gte=1, lte=50)
            ...     )
            ... )
            >>> for result in results:
            ...     print(f"[{result.score:.2f}] {result.file_name}: {result.content[:100]}")
        """
        payload: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "min_score": min_score,
        }

        if project_id:
            payload["project_id"] = project_id
        if file_ids:
            payload["file_ids"] = file_ids
        if filters:
            payload["metadata_filters"] = filters.to_api_format()

        response = self._request(
            "POST",
            f"/organizations/{self.org_id}/search/",
            json=payload,
        )

        results = [
            SearchResult(
                chunk_id=str(r.get("chunk_id", "")),
                file_id=str(r.get("file_id", "")),
                file_name=r.get("file_name", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
                chunk_index=r.get("chunk_index", 0),
                page_number=r.get("page_number"),
                start_page=r.get("start_page"),
                end_page=r.get("end_page"),
                project_id=str(r.get("project_id")) if r.get("project_id") else None,
                reference_id=r.get("reference_id"),
                category=r.get("category"),
                document_type=r.get("document_type"),
                bounding_boxes=r.get("bounding_boxes"),
            )
            for r in response.get("results", [])
        ]

        return SearchResults(
            query=response.get("query", query),
            results=results,
            total_results=response.get("total_results", len(results)),
            search_time_ms=response.get("search_time_ms", 0.0),
        )

    def _normalize_file_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize file response fields to match File model."""
        return {
            "id": str(response.get("id", "")),
            "name": response.get("name", ""),
            "original_filename": response.get("original_filename", ""),
            "size": response.get("size", 0),
            "mime_type": response.get("mime_type", ""),
            "project_id": str(response.get("project_id", "")),
            "status": response.get("status", "uploading"),
            "reference_id": response.get("reference_id"),
            "error_message": response.get("error_message"),
            "total_chunks": response.get("total_chunks", 0),
            "total_embeddings": response.get("total_embeddings", 0),
            "created_at": response.get("created_at"),
            "updated_at": response.get("updated_at"),
        }
