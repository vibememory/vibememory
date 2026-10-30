"""Conservative bitemporal helpers for retained current record versions."""

from datetime import datetime


def recorded_at(record):
    """Return when the retained current version was written, as an ISO value."""
    history = record.get("writer_history") or []
    if history and isinstance(history[-1], dict) and history[-1].get("at"):
        return history[-1]["at"]
    return record.get("created_at")


def recorded_instant(record):
    value = recorded_at(record)
    return datetime.fromisoformat(value) if value else None
