#!/usr/bin/env python3
"""Migration script for interactive terminal simplification."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "kanban.db"


def migrate():
    if not DB_PATH.exists():
        print("No database found - fresh install will use new schema.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if migration needed
    cursor.execute("PRAGMA table_info(tasks)")
    columns = {row[1] for row in cursor.fetchall()}

    if "job_output" in columns:
        print("Migrating database schema...")

        # Add new columns
        if "claude_status" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN claude_status TEXT")
        if "started_at" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN started_at TIMESTAMP")
        if "claude_completed_at" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN claude_completed_at TIMESTAMP")
        if "approved_at" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN approved_at TIMESTAMP")

        # SQLite doesn't support DROP COLUMN directly, but we can leave old columns
        # They'll be ignored by the new model

        # Migrate existing data: job_status -> claude_status
        cursor.execute("""
            UPDATE tasks SET claude_status =
                CASE job_status
                    WHEN 'running' THEN 'running'
                    WHEN 'pending' THEN 'running'
                    WHEN 'completed' THEN 'ready_for_review'
                    WHEN 'failed' THEN 'failed'
                    WHEN 'cancelled' THEN 'cancelled'
                    ELSE NULL
                END
        """)

        # Migrate timestamps
        cursor.execute("UPDATE tasks SET started_at = job_started_at WHERE job_started_at IS NOT NULL")
        cursor.execute("UPDATE tasks SET claude_completed_at = job_completed_at WHERE job_completed_at IS NOT NULL")

        conn.commit()
        print("Migration complete!")
    else:
        print("Database already migrated or fresh install.")

    conn.close()


if __name__ == "__main__":
    migrate()
