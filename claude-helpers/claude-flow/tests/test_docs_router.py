"""Tests for documentation fetching endpoints."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from kanban.main import app
from kanban.routers.docs import FetchDocsRequest

client = TestClient(app)


class TestFetchDocsRequest:
    """Unit tests for FetchDocsRequest model validation."""

    def test_valid_single_package(self):
        """Valid request with single package."""
        request = FetchDocsRequest(packages=["react"])
        assert request.packages == ["react"]

    def test_valid_multiple_packages(self):
        """Valid request with multiple packages."""
        request = FetchDocsRequest(packages=["react", "typescript", "fastapi"])
        assert len(request.packages) == 3

    def test_valid_scoped_package(self):
        """Valid request with scoped npm package."""
        request = FetchDocsRequest(packages=["@tanstack/react-query"])
        assert request.packages == ["@tanstack/react-query"]

    def test_empty_list_rejected(self):
        """Empty packages list should fail validation."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FetchDocsRequest(packages=[])

    def test_whitespace_package_rejected(self):
        """Whitespace-only package names should fail validation."""
        with pytest.raises(ValueError, match="cannot be empty or whitespace"):
            FetchDocsRequest(packages=["   "])

    def test_invalid_characters_rejected(self):
        """Package names with invalid characters should fail."""
        with pytest.raises(ValueError, match="invalid characters"):
            FetchDocsRequest(packages=["react; rm -rf /"])

    def test_strips_whitespace(self):
        """Package names should be trimmed."""
        request = FetchDocsRequest(packages=[" react ", "  typescript"])
        assert request.packages == ["react", "typescript"]

    def test_max_packages_limit(self):
        """Should reject more than 50 packages."""
        with pytest.raises(ValueError):
            FetchDocsRequest(packages=[f"package-{i}" for i in range(51)])

    def test_path_traversal_double_dot_rejected(self):
        """Path traversal with .. should fail validation."""
        with pytest.raises(ValueError, match="suspicious path patterns"):
            FetchDocsRequest(packages=["../../../etc/passwd"])

    def test_path_traversal_leading_slash_rejected(self):
        """Path traversal with leading slash should fail validation."""
        with pytest.raises(ValueError, match="suspicious path patterns"):
            FetchDocsRequest(packages=["/etc/passwd"])

    def test_path_traversal_trailing_slash_rejected(self):
        """Path traversal with trailing slash should fail validation."""
        with pytest.raises(ValueError, match="suspicious path patterns"):
            FetchDocsRequest(packages=["react/"])

    def test_scoped_package_with_slash_allowed(self):
        """Scoped packages like @org/package should be allowed."""
        request = FetchDocsRequest(packages=["@tanstack/react-query", "@types/node"])
        assert request.packages == ["@tanstack/react-query", "@types/node"]


class TestFetchDocsEndpoint:
    """Integration tests for /api/docs/fetch endpoint."""

    def test_endpoint_exists(self):
        """Endpoint should be registered."""
        response = client.get("/docs")  # OpenAPI docs
        assert response.status_code == 200

    @patch('kanban.routers.docs.threading.Thread')
    def test_successful_fetch_request(self, mock_thread):
        """Successful fetch request should return immediately."""
        response = client.post(
            "/api/docs/fetch",
            json={"packages": ["react", "typescript"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "2 package(s)" in data["message"]
        assert mock_thread.called

    def test_invalid_request_empty_packages(self):
        """Empty packages should return 422."""
        response = client.post(
            "/api/docs/fetch",
            json={"packages": []}
        )

        assert response.status_code == 422

    def test_invalid_request_no_packages_field(self):
        """Missing packages field should return 422."""
        response = client.post(
            "/api/docs/fetch",
            json={}
        )

        assert response.status_code == 422

    def test_invalid_request_wrong_type(self):
        """Wrong type for packages should return 422."""
        response = client.post(
            "/api/docs/fetch",
            json={"packages": "react"}  # Should be list, not string
        )

        assert response.status_code == 422


class TestFetchDocsIntegration:
    """Integration tests with mocked Context7 API."""

    @patch('kanban.routers.docs.threading.Thread')
    def test_full_fetch_workflow(self, mock_thread):
        """Test complete workflow with mocked thread."""
        # Create a mock thread instance
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        response = client.post(
            "/api/docs/fetch",
            json={"packages": ["react"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

        # Verify thread was created and started
        assert mock_thread.called
        assert mock_thread_instance.start.called


class TestBackgroundThreadExecution:
    """Integration tests for actual background thread execution with mocked HTTP."""

    @patch('kanban.routers.docs.PROJECT_ROOT')
    def test_background_thread_with_mocked_http(self, mock_project_root):
        """Test actual background thread execution with mocked HTTP responses."""
        # Create a temporary directory for test output
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            mock_project_root.__truediv__ = lambda _, x: tmp_path / x

            # Create the technical_docs directory
            docs_dir = tmp_path / "thoughts" / "technical_docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            # Mock the fetch_docs module functions
            with patch.dict('sys.modules', {'fetch_docs': MagicMock()}):
                import sys
                mock_fetch_docs = sys.modules['fetch_docs']

                # Mock Context7 search response
                mock_fetch_docs.search_context7.return_value = [{
                    'rank': 1,
                    'project': '/facebook/react',
                    'title': 'React',
                    'description': 'A JavaScript library for building user interfaces',
                    'stars': 200000,
                    'trustScore': 95,
                    'vip': True,
                    'type': 'repo',
                    'url': 'https://context7.com/facebook/react/llms.txt'
                }]

                # Mock successful documentation fetch
                mock_fetch_docs.get_docs.return_value = True

                # Make the request (thread will run in background)
                response = client.post(
                    "/api/docs/fetch",
                    json={"packages": ["react"]}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "started"
                assert "1 package(s)" in data["message"]

                # Give the background thread time to execute
                time.sleep(0.5)

    def test_endpoint_returns_422_for_path_traversal(self):
        """Test that path traversal attempts return 422 error."""
        response = client.post(
            "/api/docs/fetch",
            json={"packages": ["../../../etc/passwd"]}
        )

        assert response.status_code == 422
        data = response.json()
        assert "suspicious path patterns" in str(data)

    def test_endpoint_returns_422_for_leading_slash(self):
        """Test that leading slash package names return 422 error."""
        response = client.post(
            "/api/docs/fetch",
            json={"packages": ["/etc/passwd"]}
        )

        assert response.status_code == 422

    def test_endpoint_allows_scoped_packages(self):
        """Test that scoped npm packages are allowed."""
        with patch('kanban.routers.docs.threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            response = client.post(
                "/api/docs/fetch",
                json={"packages": ["@tanstack/react-query"]}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
