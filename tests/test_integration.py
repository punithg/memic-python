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


class TestSDKProjects:
    """Test /sdk/projects."""

    def test_list_projects(self, client: Memic) -> None:
        """Lists at least one project."""
        projects = client.list_projects()
        assert len(projects) >= 1
        assert projects[0].id is not None
        assert projects[0].name is not None


class TestSDKSearch:
    """Test /sdk/search."""

    def test_search_returns_results(self, client: Memic) -> None:
        """Search returns a SearchResults object."""
        results = client.search(query="test", top_k=3, min_score=0.0)
        assert isinstance(results, SearchResults)


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
            # Upload (with short timeout — it's a tiny file)
            file = client.upload_file(
                file_path=temp_path,
                wait_for_ready=True,
                poll_timeout=120,
            )
            assert file.id is not None
            assert file.status.value == "ready"

            # Verify status endpoint works
            status = client.get_file_status(file.id)
            assert status.id == file.id

            # Clean up — delete the file
            client._request("DELETE", f"/sdk/files/{file.id}")

        finally:
            Path(temp_path).unlink(missing_ok=True)
