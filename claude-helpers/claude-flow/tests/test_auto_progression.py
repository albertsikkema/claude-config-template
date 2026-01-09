"""Smoke tests for auto-progression feature.

These tests cover the critical paths of the auto-progression functionality:
1. Successful auto-progression from Implementation to Review
2. Configuration disabled - auto-progression skipped
3. Race condition detection - task stage already changed
4. Task not found handling
5. Stage transition validation (prevent backward progression)
6. Configuration API endpoints
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from kanban.main import app
from kanban.models import (
    AUTO_PROGRESSION_CONFIG,
    JobStatus,
    Stage,
    StageAutoProgressionConfig,
)

client = TestClient(app)


class TestAutoProgressTask:
    """Unit tests for auto_progress_task function."""

    @patch("kanban.jobs.SessionLocal")
    @patch("kanban.jobs.trigger_stage_command")
    def test_auto_progression_happy_path(self, mock_trigger, mock_session_local):
        """Test successful auto-progression from Implementation to Review."""
        from kanban.jobs import auto_progress_task

        # Setup mock task
        mock_task = MagicMock()
        mock_task.id = str(uuid4())
        mock_task.title = "Test Task"
        mock_task.stage = Stage.IMPLEMENTATION
        mock_task.complexity = "complete"

        # Setup mock DB session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_task
        mock_session_local.return_value = mock_db

        # Setup trigger to return True
        mock_trigger.return_value = True

        # Ensure config is enabled
        original_enabled = AUTO_PROGRESSION_CONFIG.enabled
        AUTO_PROGRESSION_CONFIG.enabled = True

        try:
            success = auto_progress_task(
                task_id=mock_task.id,
                from_stage=Stage.IMPLEMENTATION,
                to_stage=Stage.REVIEW,
            )

            assert success is True
            assert mock_task.stage == Stage.REVIEW
            assert mock_task.order == 0  # Default order from config
            mock_db.commit.assert_called_once()
            mock_trigger.assert_called_once()
        finally:
            AUTO_PROGRESSION_CONFIG.enabled = original_enabled

    @patch("kanban.jobs.SessionLocal")
    def test_auto_progression_disabled_globally(self, mock_session_local):
        """Test auto-progression respects global enabled flag."""
        from kanban.jobs import auto_progress_task

        # Disable auto-progression
        original_enabled = AUTO_PROGRESSION_CONFIG.enabled
        AUTO_PROGRESSION_CONFIG.enabled = False

        try:
            success = auto_progress_task(
                task_id=str(uuid4()),
                from_stage=Stage.IMPLEMENTATION,
                to_stage=Stage.REVIEW,
            )

            assert success is False
            # Should not even create a session when disabled
            mock_session_local.assert_not_called()
        finally:
            AUTO_PROGRESSION_CONFIG.enabled = original_enabled

    @patch("kanban.jobs.SessionLocal")
    def test_auto_progression_race_condition(self, mock_session_local):
        """Test auto-progression detects when task stage already changed."""
        from kanban.jobs import auto_progress_task

        # Setup mock task that's already in Review (race condition)
        mock_task = MagicMock()
        mock_task.id = str(uuid4())
        mock_task.title = "Test Task"
        mock_task.stage = Stage.REVIEW  # Already moved!

        # Setup mock DB session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_task
        mock_session_local.return_value = mock_db

        # Ensure config is enabled
        original_enabled = AUTO_PROGRESSION_CONFIG.enabled
        AUTO_PROGRESSION_CONFIG.enabled = True

        try:
            success = auto_progress_task(
                task_id=mock_task.id,
                from_stage=Stage.IMPLEMENTATION,  # Expected old stage
                to_stage=Stage.REVIEW,
            )

            assert success is False
            # Stage should remain unchanged (Review)
            assert mock_task.stage == Stage.REVIEW
            # Should not commit since stage verification failed
            mock_db.commit.assert_not_called()
        finally:
            AUTO_PROGRESSION_CONFIG.enabled = original_enabled

    @patch("kanban.jobs.SessionLocal")
    def test_auto_progression_task_not_found(self, mock_session_local):
        """Test auto-progression handles non-existent task gracefully."""
        from kanban.jobs import auto_progress_task

        # Setup mock DB session that returns None (task not found)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_session_local.return_value = mock_db

        # Ensure config is enabled
        original_enabled = AUTO_PROGRESSION_CONFIG.enabled
        AUTO_PROGRESSION_CONFIG.enabled = True

        try:
            success = auto_progress_task(
                task_id="00000000-0000-0000-0000-000000000000",
                from_stage=Stage.IMPLEMENTATION,
                to_stage=Stage.REVIEW,
            )

            assert success is False
            mock_db.commit.assert_not_called()
        finally:
            AUTO_PROGRESSION_CONFIG.enabled = original_enabled

    @patch("kanban.jobs.SessionLocal")
    def test_auto_progression_transition_not_configured(self, mock_session_local):
        """Test auto-progression skips unconfigured transitions."""
        from kanban.jobs import auto_progress_task

        # Ensure config is enabled but transition is not configured
        original_enabled = AUTO_PROGRESSION_CONFIG.enabled
        AUTO_PROGRESSION_CONFIG.enabled = True

        try:
            # Try a transition that's not configured (REVIEW -> CLEANUP)
            success = auto_progress_task(
                task_id=str(uuid4()),
                from_stage=Stage.REVIEW,
                to_stage=Stage.CLEANUP,
            )

            assert success is False
            # Should not even create a session for unconfigured transitions
            mock_session_local.assert_not_called()
        finally:
            AUTO_PROGRESSION_CONFIG.enabled = original_enabled


class TestStageAutoProgressionConfigValidation:
    """Tests for StageAutoProgressionConfig validation."""

    def test_valid_forward_transition(self):
        """Valid forward transition should pass validation."""
        config = StageAutoProgressionConfig(
            enabled=True,
            stage_transitions={Stage.IMPLEMENTATION: Stage.REVIEW},
        )
        assert config.stage_transitions[Stage.IMPLEMENTATION] == Stage.REVIEW

    def test_valid_multiple_forward_transitions(self):
        """Multiple valid forward transitions should pass validation."""
        config = StageAutoProgressionConfig(
            enabled=True,
            stage_transitions={
                Stage.IMPLEMENTATION: Stage.REVIEW,
                Stage.REVIEW: Stage.CLEANUP,
            },
        )
        assert len(config.stage_transitions) == 2

    def test_invalid_backward_transition_rejected(self):
        """Backward transition should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            StageAutoProgressionConfig(
                enabled=True,
                stage_transitions={Stage.REVIEW: Stage.IMPLEMENTATION},
            )

        error_str = str(exc_info.value)
        assert "Invalid stage transition" in error_str
        assert "must move forward" in error_str

    def test_invalid_same_stage_transition_rejected(self):
        """Same-stage transition should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            StageAutoProgressionConfig(
                enabled=True,
                stage_transitions={Stage.IMPLEMENTATION: Stage.IMPLEMENTATION},
            )

        error_str = str(exc_info.value)
        assert "Invalid stage transition" in error_str

    def test_invalid_done_to_backlog_rejected(self):
        """DONE -> BACKLOG transition should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            StageAutoProgressionConfig(
                enabled=True,
                stage_transitions={Stage.DONE: Stage.BACKLOG},
            )

        error_str = str(exc_info.value)
        assert "Invalid stage transition" in error_str


class TestTriggerStageCommandIdempotency:
    """Tests for trigger_stage_command idempotency protection."""

    @patch("kanban.jobs.running_jobs", {"test-task-id": MagicMock()})
    def test_idempotency_running_jobs_dict(self):
        """Test idempotency check on running_jobs dict."""
        from kanban.jobs import trigger_stage_command

        mock_db = MagicMock()

        result = trigger_stage_command(
            task_id="test-task-id",
            old_stage=Stage.IMPLEMENTATION,
            new_stage=Stage.REVIEW,
            db=mock_db,
        )

        assert result is False
        # Should not query DB if task already in running_jobs
        mock_db.query.assert_not_called()

    def test_idempotency_job_status_running(self):
        """Test idempotency check on database job_status."""
        from kanban.jobs import trigger_stage_command

        # Setup mock task with RUNNING job status
        mock_task = MagicMock()
        mock_task.id = str(uuid4())
        mock_task.job_status = JobStatus.RUNNING

        # Setup mock DB session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_task

        result = trigger_stage_command(
            task_id=mock_task.id,
            old_stage=Stage.IMPLEMENTATION,
            new_stage=Stage.REVIEW,
            db=mock_db,
        )

        assert result is False


class TestAutoProgressionConfigEndpoints:
    """Integration tests for auto-progression configuration endpoints."""

    def test_get_auto_progression_config(self):
        """Test GET /api/config/auto-progression returns current config."""
        response = client.get("/api/config/auto-progression")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "stage_transitions" in data
        assert "default_order" in data

    def test_put_auto_progression_config_valid(self):
        """Test PUT /api/config/auto-progression with valid config."""
        # Store original config
        original_enabled = AUTO_PROGRESSION_CONFIG.enabled

        try:
            response = client.put(
                "/api/config/auto-progression",
                json={
                    "enabled": False,
                    "stage_transitions": {"implementation": "review"},
                    "default_order": 5,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is False
            assert data["default_order"] == 5

            # Verify GET returns updated config
            get_response = client.get("/api/config/auto-progression")
            get_data = get_response.json()
            assert get_data["enabled"] is False
        finally:
            # Restore original config
            client.put(
                "/api/config/auto-progression",
                json={
                    "enabled": original_enabled,
                    "stage_transitions": {"implementation": "review"},
                    "default_order": 0,
                },
            )

    def test_put_auto_progression_config_invalid_backward_transition(self):
        """Test PUT /api/config/auto-progression rejects backward transition."""
        response = client.put(
            "/api/config/auto-progression",
            json={
                "enabled": True,
                "stage_transitions": {"review": "implementation"},  # Backward!
                "default_order": 0,
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "Invalid stage transition" in str(data)
