"""Tests for documentation fetching endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from kanban.main import app
from kanban.routers.docs import FetchDocsRequest, FetchDocsResponse


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
