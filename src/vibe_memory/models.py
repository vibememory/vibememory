from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Keyword = Annotated[str, Field(min_length=1, max_length=100)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KeywordsInput(Input):
    keywords: list[Keyword] = Field(min_length=1, max_length=32)

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, values):
        result, seen = [], set()
        for value in values:
            value = value.strip()
            if not value:
                raise ValueError("keywords cannot be blank")
            if value.casefold() not in seen:
                result.append(value)
                seen.add(value.casefold())
        return result


class ProvenanceInput(Input):
    source_type: Literal["agent-authored", "external", "imported"] = "agent-authored"
    origin_agent: str = Field(default="", max_length=200)
    origin_url: str = Field(default="", max_length=2048)
    collected_at: datetime | None = None
    content_type: str = Field(default="", max_length=200)
    scan_verdict: Literal["not_scanned", "safe", "suspicious", "malicious"] = "not_scanned"
    scan_evidence: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        default_factory=list, max_length=30
    )

    @field_validator("origin_url")
    @classmethod
    def valid_origin_url(cls, value):
        if not value:
            return value
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError:
            raise ValueError("origin_url must be a valid HTTP(S) URL") from None
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("origin_url must be a public HTTP(S) URL without credentials")
        return value

    @field_validator("collected_at")
    @classmethod
    def normalize_collected_at(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("collected_at must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def external_origin(self):
        if self.source_type in {"external", "imported"} and not (
            self.origin_agent or self.origin_url
        ):
            raise ValueError("external or imported records require origin_agent or origin_url")
        return self


class RecordInput(KeywordsInput):
    source: str = Field(default="", max_length=2000)
    tags: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=30
    )
    metadata: dict = Field(default_factory=dict)
    provenance: ProvenanceInput = Field(default_factory=ProvenanceInput)

    @field_validator("metadata")
    @classmethod
    def bounded_metadata(cls, value):
        import json

        if len(json.dumps(value, ensure_ascii=False, allow_nan=False)) > 30000:
            raise ValueError("metadata must fit within 30000 characters of JSON")
        return value


class MemoryInput(RecordInput):
    content: str = Field(min_length=1, max_length=10000)
    kind: Literal["fact", "preference", "event", "instruction"] = "fact"


class DocumentInput(RecordInput):
    file_id: str | None = Field(default=None, min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(default="", max_length=500000)


class EntityInput(RecordInput):
    name: str = Field(min_length=1, max_length=300)
    entity_type: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=10000)


class RelationInput(Input):
    source_id: str = Field(min_length=1, max_length=100)
    target_id: str = Field(min_length=1, max_length=100)
    relation: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("relation")
    @classmethod
    def reserved(cls, value):
        if value in {"CHUNK_OF", "KEYWORD_OF"}:
            raise ValueError("reserved internal relationship")
        return value


class RelationUpdate(Input):
    status: Literal["active", "retracted"]
    reason: str = Field(min_length=1, max_length=1000)
    expected_version: int = Field(ge=1)


class KeywordUpdate(KeywordsInput):
    """Replace an agent-supplied keyword index without analyzing original content."""


class RecordUpdate(Input):
    expected_version: int = Field(ge=1)
    content: str | None = Field(default=None, max_length=500000)
    title: str | None = Field(default=None, max_length=300)
    subtype: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=2000)
    tags: list[Annotated[str, Field(min_length=1, max_length=80)]] | None = Field(
        default=None, max_length=30
    )
    keywords: list[Keyword] | None = Field(default=None, min_length=1, max_length=32)
    metadata: dict | None = None

    @field_validator("keywords")
    @classmethod
    def normalize_optional_keywords(cls, values):
        if values is None:
            return None
        return KeywordsInput(keywords=values).keywords

    @field_validator("metadata")
    @classmethod
    def bounded_optional_metadata(cls, value):
        if value is None:
            return None
        return RecordInput(metadata=value, keywords=["validation"]).metadata

    @model_validator(mode="after")
    def has_change(self):
        if not any(
            getattr(self, field) is not None
            for field in ("content", "title", "subtype", "source", "tags", "keywords", "metadata")
        ):
            raise ValueError("at least one record field must be supplied")
        return self


class RecordSecurityUpdate(Input):
    expected_version: int = Field(ge=1)
    trust_level: Literal["trusted", "untrusted"] | None = None
    state: Literal["active", "quarantined"] | None = None
    scan_verdict: Literal["not_scanned", "safe", "suspicious", "malicious"] | None = None
    scan_evidence: list[Annotated[str, Field(min_length=1, max_length=1000)]] | None = Field(
        default=None, max_length=30
    )
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def has_security_change(self):
        if not any(
            value is not None
            for value in (self.trust_level, self.state, self.scan_verdict, self.scan_evidence)
        ):
            raise ValueError("at least one security field must be supplied")
        return self


class RecordArchive(Input):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)


class RecordMerge(Input):
    canonical_id: str = Field(min_length=1, max_length=100)
    duplicate_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        min_length=1, max_length=50
    )
    expected_versions: dict[str, int] = Field(min_length=2, max_length=51)
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_ids(self):
        if self.canonical_id in self.duplicate_ids:
            raise ValueError("canonical_id cannot also be a duplicate")
        if len(set(self.duplicate_ids)) != len(self.duplicate_ids):
            raise ValueError("duplicate_ids must be unique")
        required = {self.canonical_id, *self.duplicate_ids}
        if set(self.expected_versions) != required or any(
            version < 1 for version in self.expected_versions.values()
        ):
            raise ValueError("expected_versions must contain every canonical and duplicate ID")
        return self


class VaultInput(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    value: str = Field(min_length=1, max_length=65536)
    description: str = Field(default="", max_length=500)


class VaultCaptureRequest(Input):
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$")
    description: str = Field(default="", max_length=500)
    expires_in: int = Field(default=900, ge=60, le=3600)


class VaultCaptureSubmit(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    value: str = Field(min_length=1, max_length=65536)


class SearchInput(KeywordsInput):
    limit: int = Field(default=8, ge=1, le=50)
    scope: Literal["all", "memories", "documents", "entities"] = "all"
    tags: list[str] = Field(default_factory=list, max_length=30)
    match_mode: Literal["semantic", "exact", "hybrid"] = "semantic"
    min_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    must_keywords: list[Keyword] = Field(default_factory=list, max_length=32)
    exclude_keywords: list[Keyword] = Field(default_factory=list, max_length=32)
    metadata_filters: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=30
    )
    created_after: datetime | None = None
    created_before: datetime | None = None
    include_untrusted: bool = False
    include_quarantined: bool = False

    @field_validator("must_keywords", "exclude_keywords")
    @classmethod
    def normalize_filter_keywords(cls, values):
        result, seen = [], set()
        for value in values:
            folded = value.casefold()
            if folded not in seen:
                result.append(value)
                seen.add(folded)
        return result

    @field_validator("created_after", "created_before")
    @classmethod
    def require_utc_timestamp(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def ordered_dates(self):
        if self.created_after and self.created_before and self.created_after > self.created_before:
            raise ValueError("created_after must not be later than created_before")
        overlap = {item.casefold() for item in self.must_keywords} & {
            item.casefold() for item in self.exclude_keywords
        }
        if overlap:
            raise ValueError("a keyword cannot be both required and excluded")
        if self.include_quarantined and not self.include_untrusted:
            raise ValueError("include_quarantined requires include_untrusted")
        return self


class FeatureRequestInput(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    agent_name: str = Field(min_length=1, max_length=100)
    use_case: str = Field(default="", max_length=4000)
    priority: Literal["low", "medium", "high"] = "medium"
    source: str = Field(default="", max_length=2000)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=100)


class AgentMessageInput(Input):
    recipient_agent_id: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    subject: str = Field(default="", max_length=200)
    kind: Literal["message", "request", "response", "notification"] = "message"
    metadata: dict = Field(default_factory=dict)
    reply_to: str | None = Field(default=None, min_length=1, max_length=100)
    thread_id: str | None = Field(default=None, min_length=1, max_length=100)
    expires_in_seconds: int = Field(default=604800, ge=60, le=2592000)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("metadata")
    @classmethod
    def bounded_metadata(cls, value):
        import json

        if len(json.dumps(value, ensure_ascii=False, allow_nan=False)) > 30000:
            raise ValueError("metadata must fit within 30000 characters of JSON")
        return value


class AgentMessageAck(Input):
    status: Literal["delivered", "read", "acked"]
