"""Pytest configuration and fixtures for Claude Flow tests."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def temp_project_root(tmp_path_factory):
    """Create a temporary project root with required directories."""
    root = tmp_path_factory.mktemp("project")

    # Create required directories
    (root / "thoughts" / "shared" / "reviews").mkdir(parents=True)
    (root / ".claude" / "commands").mkdir(parents=True)

    # Create a minimal security command file
    security_cmd = root / ".claude" / "commands" / "security.md"
    security_cmd.write_text("Test security command prompt")

    return root


@pytest.fixture(scope="session")
def test_app(temp_project_root):
    """Create test FastAPI application with mocked PROJECT_ROOT."""
    # Patch PROJECT_ROOT before importing the app
    import kanban.utils as utils

    original_root = utils.PROJECT_ROOT
    utils.PROJECT_ROOT = temp_project_root

    # Also patch in the security router module
    import kanban.routers.security as security

    security.PROJECT_ROOT = temp_project_root

    from kanban.main import app

    yield app

    # Restore original
    utils.PROJECT_ROOT = original_root
    security.PROJECT_ROOT = original_root


@pytest.fixture
def client(test_app):
    """Create test client for the FastAPI application."""
    return TestClient(test_app)


@pytest.fixture
def sample_security_report(temp_project_root):
    """Create a sample security report file for testing."""
    reviews_dir = temp_project_root / "thoughts" / "shared" / "reviews"
    report_path = reviews_dir / "security-analysis-2026-01-09.md"
    report_content = """---
date: 2026-01-09
status: complete
---

# Security Analysis

## Summary

This is a test security report.

## Findings

- No critical issues found
- 2 warnings identified
"""
    report_path.write_text(report_content)
    yield report_path
    # Cleanup
    if report_path.exists():
        report_path.unlink()
