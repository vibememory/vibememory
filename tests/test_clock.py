from datetime import UTC, datetime, timedelta

from vibe_memory.clock import utc_epoch_seconds, utc_now_iso


def test_canonical_clock_is_explicit_utc():
    parsed = datetime.fromisoformat(utc_now_iso())
    assert parsed.utcoffset() == timedelta(0)
    assert parsed.tzinfo is UTC
    assert abs(utc_epoch_seconds() - int(datetime.now(UTC).timestamp())) <= 1
