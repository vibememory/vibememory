"""Canonical UTC time helpers for every persisted server timestamp."""

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """Return an explicitly offset-aware ISO 8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def utc_epoch_seconds() -> int:
    """Return Unix epoch seconds; epoch values are absolute UTC instants."""
    return int(datetime.now(UTC).timestamp())
