from vibe_memory.storage_usage import (
    RECORD_FIELDS,
    file_payload_bytes,
    payload_bytes,
    value_bytes,
)


def test_logical_payload_size_is_utf8_and_backend_independent():
    postgres_record = {
        "title": "한글",
        "metadata": {"b": 2, "a": "값"},
        "tags": ["one", "둘"],
    }
    kuzu_record = {
        "title": "한글",
        "metadata": '{"b": 2, "a": "값"}',
        "tags": ["one", "둘"],
    }

    assert value_bytes("한글") == len("한글".encode())
    assert payload_bytes(postgres_record, RECORD_FIELDS) == payload_bytes(
        kuzu_record, RECORD_FIELDS
    )


def test_file_payload_size_rejects_invalid_or_negative_metadata():
    assert file_payload_bytes({"size_bytes": "2048"}) == 2048
    assert file_payload_bytes('{"size_bytes": 12}') == 12
    assert file_payload_bytes({"size_bytes": -1}) == 0
    assert file_payload_bytes("not-json") == 0
