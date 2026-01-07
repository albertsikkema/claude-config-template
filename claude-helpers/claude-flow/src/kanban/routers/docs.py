"""Documentation management endpoints."""

import logging
import threading
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

# Project root for accessing fetch-docs.py
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

router = APIRouter(prefix="/api", tags=["docs"])
logger = logging.getLogger(__name__)


class FetchDocsRequest(BaseModel):
    """Request to fetch technical documentation."""

    packages: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of package names to fetch documentation for"
    )

    @field_validator('packages')
    @classmethod
    def validate_packages(cls, v: list[str]) -> list[str]:
        """Validate package names are non-empty and properly formatted."""
        if not v:
            raise ValueError("Packages list cannot be empty")

        cleaned = []
        for pkg in v:
            pkg_clean = pkg.strip()
            if not pkg_clean:
                raise ValueError("Package names cannot be empty or whitespace")

            # Allow alphanumeric, hyphens, underscores, @, and / (for scoped packages)
            if not all(c.isalnum() or c in '-_@/.' for c in pkg_clean):
                raise ValueError(
                    f"Package name '{pkg_clean}' contains invalid characters. "
                    "Only alphanumeric, hyphens, underscores, @, /, and . are allowed."
                )

            cleaned.append(pkg_clean)

        return cleaned


class FetchDocsResponse(BaseModel):
    """Response from documentation fetch request."""

    status: str = Field(..., description="Status of the request (e.g., 'started', 'error')")
    message: str = Field(..., description="Human-readable message describing the result")


@router.post("/docs/fetch", response_model=FetchDocsResponse)
def fetch_technical_docs(request: FetchDocsRequest):
    """Fetch technical documentation from Context7 in background.

    This is a fire-and-forget endpoint. It spawns a background thread to fetch
    documentation and returns immediately. Users should check the
    thoughts/technical_docs/ directory for downloaded files.

    Args:
        request: FetchDocsRequest with list of package names

    Returns:
        FetchDocsResponse with status 'started' and message

    Raises:
        HTTPException 400: Invalid request (caught by Pydantic validation)
    """
    # Check that target directory exists
    docs_dir = PROJECT_ROOT / "thoughts" / "technical_docs"
    if not docs_dir.exists():
        logger.info(f"Creating documentation directory: {docs_dir}")
        docs_dir.mkdir(parents=True, exist_ok=True)

    package_count = len(request.packages)
    logger.info(f"Received fetch request for {package_count} package(s): {request.packages}")

    def run_fetch():
        """Background thread function to fetch documentation."""
        import sys

        # Add claude-helpers to path to import fetch-docs
        sys.path.insert(0, str(PROJECT_ROOT / "claude-helpers"))

        try:
            from fetch_docs import get_docs, search_context7

            logger.info(f"Starting documentation fetch for {package_count} packages")

            for package in request.packages:
                try:
                    logger.info(f"Searching Context7 for package: {package}")
                    results = search_context7(package, limit=5)

                    if not results:
                        logger.warning(f"No Context7 results found for package: {package}")
                        continue

                    # Use first result (simple first-match strategy)
                    best_match = results[0]
                    project_path = best_match['project']

                    logger.info(
                        f"Found match for {package}: {best_match['title']} "
                        f"(stars: {best_match['stars']}, trust: {best_match['trustScore']})"
                    )

                    # Fetch documentation
                    success = get_docs(project_path, package, overwrite=True)
                    if success:
                        logger.info(f"Successfully fetched documentation for {package}")
                    else:
                        logger.warning(f"Failed to fetch documentation for {package}")

                except Exception as e:
                    logger.error(f"Error fetching documentation for {package}: {e}", exc_info=True)
                    # Continue with next package instead of failing entire batch

            logger.info(f"Completed documentation fetch for {package_count} packages")

        except Exception as e:
            logger.error(f"Critical error in documentation fetch thread: {e}", exc_info=True)

    # Spawn daemon thread (exits when main process exits)
    thread = threading.Thread(target=run_fetch, daemon=True)
    thread.start()

    return FetchDocsResponse(
        status="started",
        message=f"Fetching documentation for {package_count} package(s). "
                f"Files will appear in thoughts/technical_docs/"
    )
