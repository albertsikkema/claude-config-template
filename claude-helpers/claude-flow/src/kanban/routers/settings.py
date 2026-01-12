"""Application settings endpoints."""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from kanban.database import SettingDB, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

# Known setting keys
SETTING_OPENAI_API_KEY = "openai_api_key"

# Validation pattern for setting keys: lowercase letters, numbers, underscores
# Must start with a letter, max 100 characters
VALID_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,99}$")


def validate_setting_key(key: str) -> None:
    """Validate that a setting key matches the allowed pattern.

    Args:
        key: Setting key to validate

    Raises:
        HTTPException: If key format is invalid
    """
    if not VALID_KEY_PATTERN.match(key):
        raise HTTPException(
            status_code=400,
            detail="Invalid setting key format. Must be lowercase letters, numbers, "
            "and underscores, starting with a letter (max 100 chars).",
        )


def mask_sensitive_value(key: str, value: str | None) -> str | None:
    """Mask sensitive values like API keys for display.

    Args:
        key: Setting key (used to determine if masking is needed)
        value: Setting value to potentially mask

    Returns:
        Masked value if sensitive, original value otherwise
    """
    if value is None:
        return None
    if "api_key" in key or "secret" in key or "password" in key:
        return "..." + value[-4:] if len(value) > 4 else "****"
    return value


class SettingValue(BaseModel):
    """A single setting value."""

    key: str
    value: str | None


class SettingsResponse(BaseModel):
    """Response containing multiple settings."""

    settings: dict[str, str | None]


class UpdateSettingRequest(BaseModel):
    """Request to update a setting."""

    value: str | None = Field(default=None)


def get_setting(db: Session, key: str) -> str | None:
    """Get a setting value from the database.

    Args:
        db: Database session
        key: Setting key

    Returns:
        Setting value or None if not found
    """
    setting = db.query(SettingDB).filter(SettingDB.key == key).first()
    return setting.value if setting else None


def set_setting(db: Session, key: str, value: str | None) -> None:
    """Set a setting value in the database.

    Args:
        db: Database session
        key: Setting key
        value: Setting value (None to delete)
    """
    setting = db.query(SettingDB).filter(SettingDB.key == key).first()

    if value is None:
        # Delete the setting
        if setting:
            db.delete(setting)
            db.commit()
    else:
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = SettingDB(key=key, value=value)
            db.add(setting)
        db.commit()


@router.get("", response_model=SettingsResponse)
def get_all_settings(db: Session = Depends(get_db)):
    """Get all application settings.

    Returns a dictionary of all settings. API keys are masked for security.
    """
    settings = db.query(SettingDB).all()
    result = {setting.key: mask_sensitive_value(setting.key, setting.value) for setting in settings}
    return SettingsResponse(settings=result)


@router.get("/{key}", response_model=SettingValue)
def get_setting_by_key(key: str, db: Session = Depends(get_db)):
    """Get a specific setting by key.

    API keys are masked for security.
    """
    validate_setting_key(key)
    value = get_setting(db, key)
    return SettingValue(key=key, value=mask_sensitive_value(key, value))


@router.put("/{key}", response_model=SettingValue)
def update_setting_by_key(
    key: str,
    request: UpdateSettingRequest,
    db: Session = Depends(get_db),
):
    """Update a specific setting.

    Set value to null to delete the setting.
    """
    validate_setting_key(key)
    set_setting(db, key, request.value)
    # SECURITY: Never log setting values - they may contain secrets
    logger.info(f"Setting updated: {key}")
    return SettingValue(key=key, value=mask_sensitive_value(key, request.value))


@router.delete("/{key}")
def delete_setting_by_key(key: str, db: Session = Depends(get_db)):
    """Delete a specific setting."""
    validate_setting_key(key)
    set_setting(db, key, None)
    # SECURITY: Never log setting values - they may contain secrets
    logger.info(f"Setting deleted: {key}")
    return {"status": "deleted", "key": key}


# Convenience functions for use by other modules


def retrieve_setting(key: str) -> str | None:
    """Retrieve a setting value from the database.

    This is a convenience function that creates its own session.

    Args:
        key: Setting key to retrieve

    Returns:
        Setting value or None if not found
    """
    from kanban.database import SessionLocal

    db = SessionLocal()
    try:
        return get_setting(db, key)
    finally:
        db.close()
