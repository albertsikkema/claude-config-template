"""Tests for security check API endpoints."""


class TestStartSecurityCheck:
    """Tests for POST /api/security/check endpoint."""

    def test_start_security_check_returns_started_status(self, client, temp_project_root):
        """Test that starting a security check returns correct response structure."""
        response = client.post(
            "/api/security/check",
            json={"repo_id": str(temp_project_root)}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "started"
        assert "message" in data
        assert "Report will appear" in data["message"]


class TestListSecurityReports:
    """Tests for GET /api/security/checks endpoint."""

    def test_list_reports_empty_when_no_reports_exist(self, client, temp_project_root):
        """Test that GET /api/security/checks returns empty list when no reports exist."""
        response = client.get(f"/api/security/checks?repo_id={temp_project_root}")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_reports_returns_existing_reports(
        self, client, temp_project_root, sample_security_report  # noqa: ARG002
    ):
        """Test that GET /api/security/checks returns list of existing reports."""
        # sample_security_report fixture creates the file as a side effect
        response = client.get(f"/api/security/checks?repo_id={temp_project_root}")
        assert response.status_code == 200

        reports = response.json()
        assert len(reports) == 1
        assert reports[0]["filename"] == "security-analysis-2026-01-09.md"
        assert "created_at" in reports[0]
        assert "size_bytes" in reports[0]
        assert reports[0]["size_bytes"] > 0

    def test_list_reports_sorted_by_date_descending(self, client, temp_project_root):
        """Test that reports are sorted by modification time (most recent first)."""
        reviews_dir = temp_project_root / "thoughts" / "shared" / "reviews"

        # Create older report
        older = reviews_dir / "security-analysis-2026-01-01.md"
        older.write_text("Older report")

        # Create newer report
        newer = reviews_dir / "security-analysis-2026-01-08.md"
        newer.write_text("Newer report")

        response = client.get(f"/api/security/checks?repo_id={temp_project_root}")
        reports = response.json()

        assert len(reports) == 2
        # Newer report should be first (sorted by mtime, not filename)
        assert reports[0]["filename"] == "security-analysis-2026-01-08.md"
        assert reports[1]["filename"] == "security-analysis-2026-01-01.md"

        # Cleanup
        older.unlink()
        newer.unlink()


class TestGetSecurityReport:
    """Tests for GET /api/security/report/{filename} endpoint."""

    def test_get_report_returns_content(
        self, client, temp_project_root, sample_security_report  # noqa: ARG002
    ):
        """Test that GET /api/security/report/{filename} returns report content."""
        # sample_security_report fixture creates the file as a side effect
        response = client.get(
            f"/api/security/report/security-analysis-2026-01-09.md?repo_id={temp_project_root}"
        )
        assert response.status_code == 200

        data = response.json()
        assert "content" in data
        assert "path" in data
        assert "# Security Analysis" in data["content"]
        assert "security-analysis-2026-01-09.md" in data["path"]

    def test_get_report_404_for_nonexistent_file(self, client, temp_project_root):
        """Test that GET /api/security/report/{filename} returns 404 for missing files."""
        response = client.get(
            f"/api/security/report/security-analysis-2099-01-01.md?repo_id={temp_project_root}"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_report_prevents_path_traversal_with_slash(self, client, temp_project_root):
        """Test that path traversal with forward slash is blocked."""
        # Note: Forward slash in filename is handled by FastAPI routing (404)
        # or our validation (400). Either is acceptable security behavior.
        response = client.get(
            f"/api/security/report/../../../etc/passwd?repo_id={temp_project_root}"
        )
        assert response.status_code in [400, 404]

    def test_get_report_prevents_path_traversal_with_backslash(self, client, temp_project_root):
        """Test that path traversal with backslash is blocked."""
        response = client.get(
            f"/api/security/report/..\\..\\..\\etc\\passwd?repo_id={temp_project_root}"
        )
        assert response.status_code == 400
        assert "Invalid filename" in response.json()["detail"]

    def test_get_report_prevents_path_traversal_with_dotdot(self, client, temp_project_root):
        """Test that path traversal with .. is blocked."""
        response = client.get(
            f"/api/security/report/security-analysis-..md?repo_id={temp_project_root}"
        )
        assert response.status_code == 400
        assert "Invalid filename" in response.json()["detail"]

    def test_get_report_rejects_invalid_prefix(self, client, temp_project_root):
        """Test that files not starting with security-analysis- are rejected."""
        response = client.get(
            f"/api/security/report/random-file.md?repo_id={temp_project_root}"
        )
        assert response.status_code == 400
        assert "Invalid filename format" in response.json()["detail"]
        assert "security-analysis-" in response.json()["detail"]

    def test_get_report_rejects_invalid_suffix(self, client, temp_project_root):
        """Test that files not ending with .md are rejected."""
        response = client.get(
            f"/api/security/report/security-analysis-2026-01-09.txt?repo_id={temp_project_root}"
        )
        assert response.status_code == 400
        assert "Invalid filename format" in response.json()["detail"]

    def test_get_report_rejects_empty_filename(self, client, temp_project_root):
        """Test that empty filename is handled correctly."""
        # Note: This may result in 404 or 400 depending on routing
        response = client.get(f"/api/security/report/?repo_id={temp_project_root}")
        assert response.status_code in [400, 404]


class TestSecurityValidation:
    """Tests for security-related input validation."""

    def test_traversal_patterns_blocked(self, client, temp_project_root):
        """Test various path traversal attack patterns are blocked."""
        malicious_filenames = [
            "../security-analysis-2026-01-09.md",
            "security-analysis-2026-01-09.md/../../etc/passwd",
            "....//....//etc/passwd",
            "%2e%2e%2fsecurity-analysis-2026-01-09.md",  # URL encoded traversal
            "security-analysis-2026-01-09.md%00.txt",  # URL encoded null byte
        ]

        for filename in malicious_filenames:
            response = client.get(f"/api/security/report/{filename}?repo_id={temp_project_root}")
            # Should be blocked with 400 or 404, never 200
            assert response.status_code != 200, f"Failed for: {filename}"

    def test_only_security_analysis_files_allowed(self, client, temp_project_root):
        """Test that only properly named security analysis files are allowed."""
        invalid_filenames = [
            "README.md",
            "code-review-2026-01-09.md",
            "security-report.md",
            "security-analysis.md",  # Missing date
            ".security-analysis-2026-01-09.md",  # Hidden file
        ]

        for filename in invalid_filenames:
            response = client.get(f"/api/security/report/{filename}?repo_id={temp_project_root}")
            # Should be blocked with 400 (invalid format)
            assert response.status_code == 400, f"Should reject: {filename}"
