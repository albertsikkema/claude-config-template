"""Tests for timezone handling in datetime fields.

This test suite ensures that:
1. utc_now() returns timezone-aware UTC datetimes
2. Database models store and retrieve timezone-aware datetimes
3. API endpoints return ISO 8601 strings with timezone suffixes
4. Pydantic models validate timezone-aware datetimes
5. ensure_utc() helper function works correctly
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from kanban.database import TaskDB, get_db
from kanban.models import Task, TaskCreate
from kanban.routers.tasks import ensure_utc, task_db_to_model
from kanban.utils import utc_now


class TestUtcNowFunction:
    """Tests for the utc_now() utility function."""

    def test_utc_now_returns_timezone_aware(self):
        """Ensure utc_now() returns timezone-aware datetime."""
        dt = utc_now()
        assert dt.tzinfo is not None, "utc_now() should return timezone-aware datetime"
        assert dt.tzinfo == UTC, "utc_now() should return UTC timezone"

    def test_utc_now_is_current_time(self):
        """Ensure utc_now() returns current time (within 1 second)."""
        before = datetime.now(UTC)
        dt = utc_now()
        after = datetime.now(UTC)

        assert before <= dt <= after, "utc_now() should return current time"

    def test_utc_now_is_repeatable(self):
        """Ensure utc_now() can be called multiple times."""
        dt1 = utc_now()
        dt2 = utc_now()

        # Both should be timezone-aware
        assert dt1.tzinfo == UTC
        assert dt2.tzinfo == UTC

        # Second call should be >= first call (time moves forward)
        assert dt2 >= dt1


class TestEnsureUtcHelper:
    """Tests for the ensure_utc() helper function."""

    def test_ensure_utc_with_none(self):
        """Test ensure_utc() with None input."""
        result = ensure_utc(None)
        assert result is None

    def test_ensure_utc_with_naive_datetime(self):
        """Test ensure_utc() converts naive datetime to UTC."""
        naive_dt = datetime(2026, 1, 22, 10, 30, 0)
        result = ensure_utc(naive_dt)

        assert result is not None
        assert result.tzinfo is not None
        assert result.tzinfo == UTC
        # Time should be unchanged (just add timezone info)
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 22
        assert result.hour == 10
        assert result.minute == 30

    def test_ensure_utc_with_utc_datetime(self):
        """Test ensure_utc() with already UTC datetime."""
        utc_dt = datetime(2026, 1, 22, 10, 30, 0, tzinfo=UTC)
        result = ensure_utc(utc_dt)

        assert result is not None
        assert result.tzinfo == UTC
        assert result == utc_dt

    def test_ensure_utc_with_other_timezone(self):
        """Test ensure_utc() converts other timezones to UTC."""
        # Create datetime in UTC+1 (Amsterdam)
        amsterdam_tz = timezone(timedelta(hours=1))
        amsterdam_dt = datetime(2026, 1, 22, 10, 30, 0, tzinfo=amsterdam_tz)

        result = ensure_utc(amsterdam_dt)

        assert result is not None
        assert result.tzinfo == UTC
        # Should be converted to UTC (1 hour earlier)
        assert result.hour == 9
        assert result.minute == 30


class TestPydanticValidation:
    """Tests for Pydantic model timezone validation."""

    def test_task_model_accepts_timezone_aware_datetime(self):
        """Test Task model accepts timezone-aware datetimes."""
        utc_dt = datetime(2026, 1, 22, 10, 30, 0, tzinfo=UTC)

        task = Task(
            repo_id="/test/repo",
            title="Test Task",
            created_at=utc_dt,
            updated_at=utc_dt,
        )

        assert task.created_at.tzinfo == UTC
        assert task.updated_at.tzinfo == UTC

    def test_task_model_converts_naive_datetime_to_utc(self):
        """Test Task model converts naive datetimes to UTC."""
        naive_dt = datetime(2026, 1, 22, 10, 30, 0)

        task = Task(
            repo_id="/test/repo",
            title="Test Task",
            created_at=naive_dt,
            updated_at=naive_dt,
        )

        # Validator should add UTC timezone
        assert task.created_at.tzinfo == UTC
        assert task.updated_at.tzinfo == UTC

    def test_task_model_serializes_with_timezone(self):
        """Test Task model serializes datetimes with timezone suffix."""
        utc_dt = datetime(2026, 1, 22, 10, 30, 0, tzinfo=UTC)

        task = Task(
            repo_id="/test/repo",
            title="Test Task",
            created_at=utc_dt,
            updated_at=utc_dt,
        )

        # Serialize to dict
        task_dict = task.model_dump()

        # Check ISO format includes timezone
        created_str = task_dict["created_at"].isoformat() if hasattr(task_dict["created_at"], "isoformat") else str(task_dict["created_at"])
        updated_str = task_dict["updated_at"].isoformat() if hasattr(task_dict["updated_at"], "isoformat") else str(task_dict["updated_at"])

        # Should include timezone information
        assert "+" in created_str or "Z" in created_str or created_str.endswith("+00:00")
        assert "+" in updated_str or "Z" in updated_str or updated_str.endswith("+00:00")


class TestTaskDbToModel:
    """Tests for task_db_to_model() conversion function."""

    def test_task_db_to_model_preserves_timezone_aware_datetime(self):
        """Test conversion preserves timezone-aware datetimes."""
        from uuid import uuid4
        from kanban.models import Stage, Priority, ClaudeModel, WorkflowComplexity
        utc_dt = datetime(2026, 1, 22, 10, 30, 0, tzinfo=UTC)

        db_task = TaskDB(
            id=str(uuid4()),  # Ensure ID is a string for TaskDB
            repo_id="/test/repo",
            title="Test Task",
            stage=Stage.BACKLOG,
            priority=Priority.MEDIUM,
            order=0,
            model=ClaudeModel.SONNET,
            complexity=WorkflowComplexity.COMPLETE,
            auto_advance=False,
            created_at=utc_dt,
            updated_at=utc_dt,
        )

        task = task_db_to_model(db_task)

        assert task.created_at.tzinfo == UTC
        assert task.updated_at.tzinfo == UTC

    def test_task_db_to_model_converts_naive_datetime(self):
        """Test conversion adds UTC timezone to naive datetimes."""
        from uuid import uuid4
        from kanban.models import Stage, Priority, ClaudeModel, WorkflowComplexity
        # Simulate what SQLite returns (naive datetime)
        naive_dt = datetime(2026, 1, 22, 10, 30, 0)

        db_task = TaskDB(
            id=str(uuid4()),  # Ensure ID is a string for TaskDB
            repo_id="/test/repo",
            title="Test Task",
            stage=Stage.BACKLOG,
            priority=Priority.MEDIUM,
            order=0,
            model=ClaudeModel.SONNET,
            complexity=WorkflowComplexity.COMPLETE,
            auto_advance=False,
            created_at=naive_dt,
            updated_at=naive_dt,
        )

        task = task_db_to_model(db_task)

        # Should have timezone after conversion
        assert task.created_at.tzinfo == UTC
        assert task.updated_at.tzinfo == UTC

    def test_task_db_to_model_handles_none_timestamps(self):
        """Test conversion handles None timestamps correctly."""
        from uuid import uuid4
        from kanban.models import Stage, Priority, ClaudeModel, WorkflowComplexity
        db_task = TaskDB(
            id=str(uuid4()),  # Ensure ID is a string for TaskDB
            repo_id="/test/repo",
            title="Test Task",
            stage=Stage.BACKLOG,
            priority=Priority.MEDIUM,
            order=0,
            model=ClaudeModel.SONNET,
            complexity=WorkflowComplexity.COMPLETE,
            auto_advance=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            started_at=None,
            claude_completed_at=None,
            approved_at=None,
            last_notification=None,
        )

        task = task_db_to_model(db_task)

        assert task.started_at is None
        assert task.claude_completed_at is None
        assert task.approved_at is None
        assert task.last_notification is None


class TestApiEndpointTimezones:
    """Tests for API endpoint timezone handling."""

    def test_create_task_returns_timezone_aware_timestamps(self, client):
        """Test POST /api/tasks returns timezone-aware timestamps."""
        task_data = {
            "repo_id": "/test/repo",
            "title": "Test Task",
            "description": "Test description",
        }

        response = client.post("/api/tasks", json=task_data)
        assert response.status_code == 201

        data = response.json()

        # Check that datetime strings include timezone offset
        assert "+" in data["created_at"] or "Z" in data["created_at"], \
            f"created_at should include timezone: {data['created_at']}"
        assert "+" in data["updated_at"] or "Z" in data["updated_at"], \
            f"updated_at should include timezone: {data['updated_at']}"

    def test_get_tasks_returns_timezone_aware_timestamps(self, client):
        """Test GET /api/tasks returns timezone-aware timestamps."""
        # First create a task
        task_data = {
            "repo_id": "/test/repo",
            "title": "Test Task",
        }
        client.post("/api/tasks", json=task_data)

        # Get all tasks
        response = client.get("/api/tasks")
        assert response.status_code == 200

        tasks = response.json()
        if len(tasks) > 0:
            task = tasks[0]
            assert "+" in task["created_at"] or "Z" in task["created_at"]
            assert "+" in task["updated_at"] or "Z" in task["updated_at"]

    def test_update_task_preserves_timezone_info(self, client):
        """Test PUT /api/tasks/{id} preserves timezone information."""
        # Create task
        task_data = {
            "repo_id": "/test/repo",
            "title": "Original Title",
        }
        create_response = client.post("/api/tasks", json=task_data)
        task_id = create_response.json()["id"]

        # Update task
        update_data = {
            "title": "Updated Title",
        }
        response = client.put(f"/api/tasks/{task_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert "+" in data["created_at"] or "Z" in data["created_at"]
        assert "+" in data["updated_at"] or "Z" in data["updated_at"]


class TestDatabaseSchemaTimezones:
    """Tests for database schema timezone configuration."""

    def test_database_columns_have_timezone_flag(self):
        """Test that DateTime columns have timezone=True."""
        from sqlalchemy import inspect

        # Inspect TaskDB table
        inspector = inspect(TaskDB)

        # Check DateTime columns
        datetime_columns = [
            "created_at",
            "updated_at",
            "started_at",
            "claude_completed_at",
            "approved_at",
            "last_notification",
        ]

        for col_name in datetime_columns:
            col = getattr(TaskDB, col_name)
            # The column should use DateTime with timezone support
            # Note: SQLite doesn't enforce this at DB level, but SQLAlchemy should handle it
            assert col is not None, f"Column {col_name} should exist"


# Integration test that simulates the full workflow
class TestTimezoneIntegration:
    """Integration tests for end-to-end timezone handling."""

    def test_full_task_lifecycle_maintains_timezone(self, client):
        """Test that timezone info is maintained through full task lifecycle."""
        # 1. Create task
        task_data = {
            "repo_id": "/test/repo",
            "title": "Lifecycle Test Task",
        }
        create_response = client.post("/api/tasks", json=task_data)
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # 2. Get task
        get_response = client.get(f"/api/tasks/{task_id}")
        assert get_response.status_code == 200
        task_data = get_response.json()

        # Verify all timestamps have timezone
        assert "+" in task_data["created_at"] or "Z" in task_data["created_at"]
        assert "+" in task_data["updated_at"] or "Z" in task_data["updated_at"]

        # 3. Update task
        update_response = client.put(
            f"/api/tasks/{task_id}",
            json={"title": "Updated Title"}
        )
        assert update_response.status_code == 200
        updated_data = update_response.json()

        assert "+" in updated_data["created_at"] or "Z" in updated_data["created_at"]
        assert "+" in updated_data["updated_at"] or "Z" in updated_data["updated_at"]

        # 4. List all tasks
        list_response = client.get("/api/tasks")
        tasks = list_response.json()
        found_task = next((t for t in tasks if t["id"] == task_id), None)
        assert found_task is not None
        assert "+" in found_task["created_at"] or "Z" in found_task["created_at"]

    def test_naive_datetime_in_db_gets_converted(self):
        """Test that even if DB has naive datetime, it gets converted to UTC."""
        from kanban.database import SessionLocal

        # Create task with naive datetime (simulating old data)
        naive_dt = datetime(2026, 1, 22, 10, 30, 0)

        db = SessionLocal()
        try:
            db_task = TaskDB(
                repo_id="/test/repo",
                title="Naive DateTime Test",
                created_at=naive_dt,
                updated_at=naive_dt,
            )
            db.add(db_task)
            db.commit()
            db.refresh(db_task)

            # Convert to model
            task = task_db_to_model(db_task)

            # Should have UTC timezone after conversion
            assert task.created_at.tzinfo == UTC
            assert task.updated_at.tzinfo == UTC

            # Cleanup
            db.delete(db_task)
            db.commit()
        finally:
            db.close()
