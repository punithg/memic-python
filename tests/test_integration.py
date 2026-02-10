"""Integration tests for the Memic SDK against a running backend.

These tests require:
  - A running Memic backend (local or remote)
  - An environment-scoped API key set via MEMIC_API_KEY env var

Run:
  # Against local backend
  MEMIC_API_KEY=mk_live_... MEMIC_BASE_URL=http://localhost:8000/api/v1 pytest tests/test_integration.py -v

  # Against production
  MEMIC_API_KEY=mk_live_... pytest tests/test_integration.py -v

All tests are skipped automatically if MEMIC_API_KEY is not set,
so running `pytest` in CI without the env var is safe.
"""

import os
import tempfile
from pathlib import Path

import pytest

from memic import Memic, SearchResults

# Skip entire module if no API key is configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("MEMIC_API_KEY"),
    reason="MEMIC_API_KEY not set — skipping integration tests",
)


@pytest.fixture(scope="module")
def client() -> Memic:
    """Create a real Memic client from env vars."""
    return Memic()  # reads MEMIC_API_KEY and MEMIC_BASE_URL from env


class TestSDKMe:
    """Test /sdk/me context resolution."""

    def test_context_resolves(self, client: Memic) -> None:
        """API key resolves org, project, and environment."""
        assert client.org_id is not None
        assert client.project_id is not None
        assert client.environment_slug in ("staging", "production")

    def test_response_shape(self, client: Memic) -> None:
        """Verify /sdk/me returns all expected fields."""
        response = client._request("GET", "/sdk/me")
        expected_fields = [
            "organization_id",
            "project_id",
            "environment_id",
            "environment_slug",
        ]
        for field in expected_fields:
            assert field in response, (
                f"Missing field '{field}' in /sdk/me response. "
                f"Got keys: {list(response.keys())}"
            )


class TestSDKProjects:
    """Test /sdk/projects."""

    def test_list_projects(self, client: Memic) -> None:
        """Lists at least one project."""
        projects = client.list_projects()
        assert len(projects) >= 1, (
            "Expected at least 1 project but got 0"
        )
        assert projects[0].id is not None
        assert projects[0].name is not None


class TestSDKSearch:
    """Test /sdk/search."""

    def test_search_returns_results(self, client: Memic) -> None:
        """Search returns a SearchResults object."""
        results = client.search(query="test", top_k=3, min_score=0.0)
        assert isinstance(results, SearchResults), (
            f"Expected SearchResults, got {type(results).__name__}"
        )

    def test_search_with_filters(self, client: Memic) -> None:
        """Search respects top_k and min_score parameters."""
        results = client.search(query="test", top_k=1, min_score=0.0)
        assert isinstance(results, SearchResults)
        assert len(results.results.semantic) <= 1, (
            f"top_k=1 but got {len(results.results.semantic)} results"
        )

        results_strict = client.search(query="test", top_k=5, min_score=0.99)
        assert isinstance(results_strict, SearchResults)
        # With min_score=0.99 we expect very few or no results
        assert results_strict.total_results >= 0


class TestSDKChat:
    """Test /sdk/chat endpoint."""

    def test_chat_returns_answer(self, client: Memic) -> None:
        """Chat returns a response with an answer field."""
        response = client._request(
            "POST",
            "/sdk/chat",
            json={"question": "What is this about?", "top_k": 3, "min_score": 0.0},
        )
        assert "answer" in response, (
            f"Missing 'answer' field in /sdk/chat response. "
            f"Got keys: {list(response.keys())}"
        )
        assert isinstance(response["answer"], str)
        assert len(response["answer"]) > 0, "Chat answer is empty"

        # Verify other expected response fields
        assert "question" in response
        assert "citations" in response
        assert "model" in response


class TestSDKFiles:
    """Test /sdk/files list and status endpoints."""

    def test_list_files(self, client: Memic) -> None:
        """List files returns paginated response shape."""
        response = client._request(
            "GET",
            "/sdk/files",
            params={"page": 1, "page_size": 5},
        )
        expected_fields = ["items", "total", "page", "page_size", "total_pages"]
        for field in expected_fields:
            assert field in response, (
                f"Missing field '{field}' in /sdk/files response. "
                f"Got keys: {list(response.keys())}"
            )
        assert isinstance(response["items"], list)
        assert response["page"] == 1
        assert response["page_size"] == 5

    def test_get_file_status(self, client: Memic) -> None:
        """Get file status for a known file (from list)."""
        files_response = client._request(
            "GET",
            "/sdk/files",
            params={"page": 1, "page_size": 1},
        )
        if files_response["total"] == 0:
            pytest.skip("No files in environment — cannot test file status")

        file_id = files_response["items"][0]["id"]
        status_response = client._request("GET", f"/sdk/files/{file_id}/status")
        assert "id" in status_response, (
            f"Missing 'id' in file status response. "
            f"Got keys: {list(status_response.keys())}"
        )
        assert "status" in status_response


class TestSDKFileLifecycle:
    """Test /sdk/files (init → upload → confirm → status → delete)."""

    def test_upload_and_delete(self, client: Memic) -> None:
        """Full file lifecycle: upload a small file, wait for ready, then delete."""
        # Create a tiny test file
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w"
        ) as f:
            f.write("Integration test content for Memic SDK.")
            temp_path = f.name

        try:
            # Upload (with CI-friendly timeout)
            file = client.upload_file(
                file_path=temp_path,
                wait_for_ready=True,
                poll_timeout=90,
            )
            assert file.id is not None, "Uploaded file has no ID"
            assert file.status.value == "ready", (
                f"Expected status 'ready', got '{file.status.value}'"
            )

            # Verify status endpoint works
            status = client.get_file_status(file.id)
            assert status.id == file.id

            # Clean up — delete the file
            client._request("DELETE", f"/sdk/files/{file.id}")

        finally:
            Path(temp_path).unlink(missing_ok=True)
