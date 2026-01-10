"""Tests for version endpoint."""

import re

import pytest  # noqa: F401 (pytest fixtures used via conftest)


class TestVersionEndpoint:
    """Tests for GET /api/version endpoint."""

    def test_version_endpoint_returns_200(self, client):
        """Test version endpoint returns 200 status code."""
        response = client.get("/api/version")
        assert response.status_code == 200

    def test_version_endpoint_response_structure(self, client):
        """Test version endpoint returns correct response structure."""
        response = client.get("/api/version")
        data = response.json()

        assert "version" in data
        assert "service" in data

    def test_version_endpoint_field_types(self, client):
        """Test version endpoint returns correct field types."""
        response = client.get("/api/version")
        data = response.json()

        assert isinstance(data["version"], str)
        assert isinstance(data["service"], str)

    def test_version_endpoint_service_name(self, client):
        """Test version endpoint returns correct service name."""
        response = client.get("/api/version")
        data = response.json()

        assert data["service"] == "claude-workflow-kanban"

    def test_version_endpoint_has_version_value(self, client):
        """Test version endpoint returns non-empty version string in semver format."""
        response = client.get("/api/version")
        data = response.json()

        assert len(data["version"]) > 0
        # Version should match semantic versioning (X.Y.Z) or be the fallback "unknown"
        semver_pattern = r'^\d+\.\d+\.\d+.*$|^unknown$'
        assert re.match(semver_pattern, data["version"]), \
            f"Version '{data['version']}' doesn't match expected semver format (X.Y.Z or 'unknown')"

    def test_version_endpoint_in_openapi_docs(self, client):
        """Test version endpoint appears in OpenAPI documentation."""
        response = client.get("/docs")
        assert response.status_code == 200

        # The endpoint should be documented (swagger UI is served)
        # Additional verification can be done by checking /openapi.json
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()

        # Verify endpoint is in the OpenAPI schema
        paths = openapi.get("paths", {})
        assert "/api/version" in paths
        assert "get" in paths["/api/version"]
