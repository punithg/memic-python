"""Unit tests for the Memic client."""

import os
import tempfile
from unittest.mock import patch

import pytest
import responses

from memic import (
    APIError,
    AuthenticationError,
    File,
    FileStatus,
    Memic,
    MetadataFilters,
    NotFoundError,
    PageRange,
    SearchResults,
)


@pytest.fixture
def api_key() -> str:
    return "mk_test_key_123"


@pytest.fixture
def base_url() -> str:
    return "https://api.memic.ai"


@pytest.fixture
def org_id() -> str:
    return "org-123-456"


@pytest.fixture
def project_id() -> str:
    return "proj-789-abc"


@pytest.fixture
def file_id() -> str:
    return "file-def-456"


@pytest.fixture
def client(api_key: str, base_url: str) -> Memic:
    """Create a Memic client (context is lazy-fetched, no mock needed at init)."""
    return Memic(api_key=api_key, base_url=base_url)


class TestClientInit:
    """Tests for client initialization."""

    def test_init_with_api_key(self, api_key: str) -> None:
        """Client initializes with provided API key."""
        client = Memic(api_key=api_key)
        assert client.api_key == api_key

    def test_init_from_env_var(self, api_key: str) -> None:
        """Client reads API key from environment variable."""
        with patch.dict(os.environ, {"MEMIC_API_KEY": api_key}):
            client = Memic()
            assert client.api_key == api_key

    def test_init_without_api_key_raises(self) -> None:
        """Client raises AuthenticationError without API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing MEMIC_API_KEY
            os.environ.pop("MEMIC_API_KEY", None)
            with pytest.raises(AuthenticationError, match="No API key provided"):
                Memic()

    def test_init_with_custom_base_url(self, api_key: str) -> None:
        """Client uses custom base URL."""
        custom_url = "https://custom.api.com"
        client = Memic(api_key=api_key, base_url=custom_url)
        assert client.base_url == custom_url

    def test_init_strips_trailing_slash(self, api_key: str) -> None:
        """Client strips trailing slash from base URL."""
        client = Memic(api_key=api_key, base_url="https://api.com/")
        assert client.base_url == "https://api.com"


class TestOrgIdFetch:
    """Tests for org_id auto-discovery."""

    @responses.activate
    def test_org_id_fetched_on_first_access(
        self, api_key: str, base_url: str, org_id: str
    ) -> None:
        """org_id is fetched from API on first access."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/me",
            json={"organization_id": org_id, "organization_name": "Test Org"},
            status=200,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        assert client._org_id is None  # Not fetched yet
        assert client.org_id == org_id  # Fetched on access
        assert client._org_id == org_id  # Cached

    @responses.activate
    def test_org_id_cached(self, api_key: str, base_url: str, org_id: str) -> None:
        """org_id is cached after first fetch."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/me",
            json={"organization_id": org_id},
            status=200,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        _ = client.org_id
        _ = client.org_id  # Second access

        # Only one request should be made
        assert len(responses.calls) == 1


class TestListProjects:
    """Tests for list_projects method."""

    @responses.activate
    def test_list_projects_success(
        self, api_key: str, base_url: str, org_id: str
    ) -> None:
        """list_projects returns list of Project objects."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/projects",
            json=[
                {"id": "proj-1", "name": "Project 1", "organization_id": org_id, "is_active": True},
                {"id": "proj-2", "name": "Project 2", "organization_id": org_id, "is_active": True},
            ],
            status=200,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        projects = client.list_projects()

        assert len(projects) == 2
        assert projects[0].id == "proj-1"
        assert projects[0].name == "Project 1"


class TestUploadFile:
    """Tests for upload_file method."""

    @responses.activate
    def test_upload_file_success(
        self, api_key: str, base_url: str, project_id: str, file_id: str
    ) -> None:
        """upload_file completes 3-step flow."""
        # Setup mocks
        responses.add(
            responses.POST,
            f"{base_url}/sdk/files/init",
            json={
                "file_id": file_id,
                "upload_url": "https://storage.example.com/upload",
                "expires_in": 3600,
            },
            status=201,
        )
        responses.add(
            responses.PUT,
            "https://storage.example.com/upload",
            status=200,
        )
        responses.add(
            responses.POST,
            f"{base_url}/sdk/files/{file_id}/confirm",
            json={
                "id": file_id,
                "name": "test.pdf",
                "original_filename": "test.pdf",
                "size": 1024,
                "mime_type": "application/pdf",
                "project_id": project_id,
                "status": "ready",
            },
            status=200,
        )

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            client = Memic(api_key=api_key, base_url=base_url)
            file = client.upload_file(
                file_path=temp_path,
                wait_for_ready=False,
            )

            assert file.id == file_id
            assert file.status == FileStatus.READY
        finally:
            os.unlink(temp_path)

    def test_upload_file_not_found(self, api_key: str) -> None:
        """upload_file raises FileNotFoundError for missing file."""
        client = Memic(api_key=api_key)

        with pytest.raises(FileNotFoundError, match="File not found"):
            client.upload_file(
                file_path="/nonexistent/file.pdf",
            )


class TestGetFileStatus:
    """Tests for get_file_status method."""

    @responses.activate
    def test_get_file_status_success(
        self, api_key: str, base_url: str, project_id: str, file_id: str
    ) -> None:
        """get_file_status returns File object."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/files/{file_id}/status",
            json={
                "id": file_id,
                "name": "test.pdf",
                "original_filename": "test.pdf",
                "size": 1024,
                "mime_type": "application/pdf",
                "project_id": project_id,
                "status": "parsing_started",
                "total_chunks": 5,
            },
            status=200,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        file = client.get_file_status(file_id)

        assert file.id == file_id
        assert file.status == FileStatus.PARSING_STARTED
        assert file.status.is_processing is True
        assert file.status.is_failed is False


class TestSearch:
    """Tests for search method."""

    @responses.activate
    def test_search_basic(
        self, api_key: str, base_url: str, project_id: str
    ) -> None:
        """search returns SearchResults with matching chunks."""
        responses.add(
            responses.POST,
            f"{base_url}/sdk/search",
            json={
                "query": "test query",
                "results": {
                    "semantic": [
                        {
                            "chunk_id": "chunk-1",
                            "file_id": "file-1",
                            "file_name": "doc.pdf",
                            "content": "This is the matching content",
                            "score": 0.95,
                            "chunk_index": 0,
                            "page_number": 1,
                        },
                        {
                            "chunk_id": "chunk-2",
                            "file_id": "file-1",
                            "file_name": "doc.pdf",
                            "content": "Another match",
                            "score": 0.85,
                            "chunk_index": 1,
                            "page_number": 2,
                        },
                    ],
                },
                "total_results": 2,
                "search_time_ms": 125.5,
            },
            status=200,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        results = client.search(query="test query", project_id=project_id)

        assert isinstance(results, SearchResults)
        assert len(results) == 2
        assert results.total_results == 2
        assert results.search_time_ms == 125.5
        assert results[0].score == 0.95
        assert results[0].content == "This is the matching content"

    @responses.activate
    def test_search_with_filters(
        self, api_key: str, base_url: str
    ) -> None:
        """search passes metadata filters correctly."""
        responses.add(
            responses.POST,
            f"{base_url}/sdk/search",
            json={"query": "test", "results": {"semantic": []}, "total_results": 0, "search_time_ms": 50.0},
            status=200,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        filters = MetadataFilters(
            reference_id="TG_G1_Math",
            page_range=PageRange(gte=1, lte=50),
        )
        client.search(query="test", filters=filters)

        # Check request body
        request_body = responses.calls[-1].request.body
        assert b"TG_G1_Math" in request_body
        assert b"metadata_filters" in request_body

    @responses.activate
    def test_search_iterable(
        self, api_key: str, base_url: str
    ) -> None:
        """SearchResults is iterable."""
        responses.add(
            responses.POST,
            f"{base_url}/sdk/search",
            json={
                "query": "test",
                "results": {
                    "semantic": [
                        {"chunk_id": "1", "file_id": "f1", "file_name": "a.pdf", "content": "A", "score": 0.9},
                        {"chunk_id": "2", "file_id": "f2", "file_name": "b.pdf", "content": "B", "score": 0.8},
                    ],
                },
                "total_results": 2,
                "search_time_ms": 50.0,
            },
            status=200,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        results = client.search(query="test")

        # Test iteration
        contents = [r.content for r in results]
        assert contents == ["A", "B"]


class TestExceptionHandling:
    """Tests for exception handling."""

    @responses.activate
    def test_authentication_error_401(self, api_key: str, base_url: str) -> None:
        """401 response raises AuthenticationError."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/me",
            json={"detail": "Invalid API key"},
            status=401,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        with pytest.raises(AuthenticationError, match="Invalid API key"):
            _ = client.org_id

    @responses.activate
    def test_authentication_error_403(self, api_key: str, base_url: str) -> None:
        """403 response raises AuthenticationError."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/me",
            json={"detail": "Access denied"},
            status=403,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        with pytest.raises(AuthenticationError, match="Access denied"):
            _ = client.org_id

    @responses.activate
    def test_not_found_error(
        self, api_key: str, base_url: str
    ) -> None:
        """404 response raises NotFoundError."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/files/nonexistent/status",
            json={"detail": "File not found"},
            status=404,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        with pytest.raises(NotFoundError, match="File not found"):
            client.get_file_status("nonexistent")

    @responses.activate
    def test_api_error(self, api_key: str, base_url: str) -> None:
        """500 response raises APIError."""
        responses.add(
            responses.GET,
            f"{base_url}/sdk/me",
            json={"detail": "Internal server error"},
            status=500,
        )

        client = Memic(api_key=api_key, base_url=base_url)
        with pytest.raises(APIError) as exc_info:
            _ = client.org_id

        assert exc_info.value.status_code == 500


class TestFileStatus:
    """Tests for FileStatus enum."""

    def test_is_failed_true(self) -> None:
        """is_failed returns True for failed statuses."""
        assert FileStatus.UPLOAD_FAILED.is_failed is True
        assert FileStatus.CONVERSION_FAILED.is_failed is True
        assert FileStatus.PARSING_FAILED.is_failed is True
        assert FileStatus.EMBEDDING_FAILED.is_failed is True

    def test_is_failed_false(self) -> None:
        """is_failed returns False for non-failed statuses."""
        assert FileStatus.UPLOADING.is_failed is False
        assert FileStatus.READY.is_failed is False
        assert FileStatus.PARSING_STARTED.is_failed is False

    def test_is_processing_true(self) -> None:
        """is_processing returns True for processing statuses."""
        assert FileStatus.UPLOADING.is_processing is True
        assert FileStatus.PARSING_STARTED.is_processing is True
        assert FileStatus.EMBEDDING_STARTED.is_processing is True

    def test_is_processing_false(self) -> None:
        """is_processing returns False for terminal statuses."""
        assert FileStatus.READY.is_processing is False
        assert FileStatus.UPLOAD_FAILED.is_processing is False


class TestMetadataFilters:
    """Tests for MetadataFilters."""

    def test_to_api_format_empty(self) -> None:
        """Empty filters produce empty dict."""
        filters = MetadataFilters()
        assert filters.to_api_format() == {}

    def test_to_api_format_with_values(self) -> None:
        """Filters are correctly converted to API format."""
        filters = MetadataFilters(
            reference_id="TG_G1_Math",
            page_range=PageRange(gte=1, lte=50),
            category="education",
        )
        result = filters.to_api_format()

        assert result["reference_id"] == "TG_G1_Math"
        assert result["page_range"] == {"gte": 1, "lte": 50}
        assert result["category"] == "education"
