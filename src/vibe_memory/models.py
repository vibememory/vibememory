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
    client_request_id: str | None = Field(default=None, min_length=1, max_length=100)
    source: str = Field(default="", max_length=2000)
    tags: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=30
    )
    metadata: dict = Field(default_factory=dict)
    provenance: ProvenanceInput = Field(default_factory=ProvenanceInput)
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    @field_validator("metadata")
    @classmethod
    def bounded_metadata(cls, value):
        import json

        if len(json.dumps(value, ensure_ascii=False, allow_nan=False)) > 30000:
            raise ValueError("metadata must fit within 30000 characters of JSON")
        return value

    @field_validator("valid_from", "valid_to")
    @classmethod
    def normalize_valid_time(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("valid time must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def temporal_interval(self):
        if self.valid_from and self.valid_to and self.valid_from >= self.valid_to:
            raise ValueError("valid_from must be earlier than valid_to")
        if self.valid_from is None and self.valid_to is None:
            return self
        temporal = dict(self.metadata.get("vibe_memory_temporal") or {})
        temporal.update(
            {
                "valid_from": self.valid_from.isoformat() if self.valid_from else None,
                "valid_to": self.valid_to.isoformat() if self.valid_to else None,
                "basis": "agent_supplied",
            }
        )
        self.metadata = {**self.metadata, "vibe_memory_temporal": temporal}
        return self


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


class EvidenceReference(Input):
    """Agent-observed immutable coordinates for one relationship input."""

    record_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    observed_at: datetime
    location: str = Field(default="", max_length=1000)
    range_start: int | None = Field(default=None, ge=0)
    range_end: int | None = Field(default=None, ge=0)

    @field_validator("content_hash")
    @classmethod
    def normalize_hash(cls, value):
        return value.lower()

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def valid_range(self):
        if (
            self.range_start is not None
            and self.range_end is not None
            and self.range_end < self.range_start
        ):
            raise ValueError("range_end must be greater than or equal to range_start")
        return self


class RelationInput(Input):
    source_id: str = Field(min_length=1, max_length=100)
    target_id: str = Field(min_length=1, max_length=100)
    relation: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
    reason: str = Field(min_length=1, max_length=1000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_record_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=50
    )
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=50)
    evidence_coverage: Literal["selected", "partial", "unknown"] = "unknown"
    input_manifest_id: str | None = Field(default=None, min_length=1, max_length=100)
    extraction_method: str = Field(default="", max_length=100)
    extraction_version: str = Field(default="", max_length=100)
    correction_scope: Literal["unknown", "full", "partial"] = "unknown"

    @field_validator("relation")
    @classmethod
    def reserved(cls, value):
        if value in {"CHUNK_OF", "KEYWORD_OF"}:
            raise ValueError("reserved internal relationship")
        return value

    @field_validator("evidence_record_ids")
    @classmethod
    def unique_evidence(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("evidence_record_ids must be unique")
        return values

    @model_validator(mode="after")
    def combine_evidence_ids(self):
        referenced = [item.record_id for item in self.evidence]
        snapshots = [
            (
                item.record_id,
                item.version,
                item.content_hash,
                item.location,
                item.range_start,
                item.range_end,
            )
            for item in self.evidence
        ]
        if len(snapshots) != len(set(snapshots)):
            raise ValueError("evidence snapshots must be unique")
        self.evidence_record_ids = list(
            dict.fromkeys([*self.evidence_record_ids, *referenced])
        )
        return self


class MemoryCorrectionInput(Input):
    previous_id: str = Field(min_length=1, max_length=100)
    expected_previous_version: int = Field(ge=1)
    replacement: MemoryInput
    relation: Literal["SUPERSEDES", "CORRECTS"] = "SUPERSEDES"
    correction_scope: Literal["full", "partial"] = "full"
    reason: str = Field(min_length=1, max_length=1000)
    client_request_id: str = Field(min_length=1, max_length=100)


class EntityCreateManyItem(EntityInput):
    client_request_id: str = Field(min_length=1, max_length=100)


class RelationCreateManyItem(RelationInput):
    client_request_id: str = Field(min_length=1, max_length=100)


class BatchInput(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, populate_by_name=True)
    return_mode: Literal["minimal", "full"] = Field(default="minimal", alias="return")
    atomic: bool = False

    @model_validator(mode="after")
    def partial_success_only(self):
        if self.atomic:
            raise ValueError("atomic=true is not supported; each batch item commits independently")
        return self


class EntityCreateMany(BatchInput):
    items: list[EntityCreateManyItem] = Field(min_length=1, max_length=100)


class RelationCreateMany(BatchInput):
    items: list[RelationCreateManyItem] = Field(min_length=1, max_length=100)


class VaultGrantUpdate(Input):
    names: list[Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,99}$")]] = Field(
        default_factory=list, max_length=100
    )

    @field_validator("names")
    @classmethod
    def unique_names(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Vault grant names must be unique")
        return values


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


class RecordUpdateManyItem(RecordUpdate):
    id: str = Field(min_length=1, max_length=100)
    client_request_id: str = Field(min_length=1, max_length=100)


class RecordUpdateMany(BatchInput):
    items: list[RecordUpdateManyItem] = Field(min_length=1, max_length=100)


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
    exclude_resolved_superseded: bool = False
    valid_at: datetime | None = None
    known_at: datetime | None = None

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

    @field_validator("created_after", "created_before", "valid_at", "known_at")
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


class ContextBundleInput(Input):
    """Deterministic, LLM-free handoff selection over stored records and edges."""

    anchor_id: str | None = Field(default=None, min_length=1, max_length=100)
    record_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=200
    )
    kinds: list[Literal["memory", "document", "entity", "file"]] = Field(
        default_factory=list, max_length=4
    )
    tags: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=30
    )
    relations: list[
        Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")]
    ] = Field(default_factory=list, max_length=30)
    created_after: datetime | None = None
    updated_after: datetime | None = None
    valid_at: datetime | None = None
    known_at: datetime | None = None
    depth: int = Field(default=1, ge=0, le=2)
    limit: int = Field(default=25, ge=1, le=100)
    byte_limit: int = Field(default=131072, ge=2048, le=1048576)
    cursor: str | None = Field(default=None, min_length=1, max_length=2048)
    include_content: bool = False
    include_untrusted: bool = False
    include_quarantined: bool = False

    @field_validator("record_ids", "kinds", "tags", "relations")
    @classmethod
    def unique_values(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("selector values must be unique")
        return values

    @field_validator("created_after", "updated_after", "valid_at", "known_at")
    @classmethod
    def normalize_context_time(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def safe_context_selection(self):
        if self.include_quarantined and not self.include_untrusted:
            raise ValueError("include_quarantined requires include_untrusted")
        if not any(
            (
                self.anchor_id,
                self.record_ids,
                self.kinds,
                self.tags,
                self.created_after,
                self.updated_after,
                self.valid_at,
                self.known_at,
            )
        ):
            raise ValueError("at least one context selector is required")
        return self


class GraphAuditInput(Input):
    include_untrusted: bool = False
    include_quarantined: bool = False
    relation: str = Field(default="", max_length=80, pattern=r"^$|^[A-Z][A-Z0-9_]*$")
    hub_threshold: int = Field(default=20, ge=2, le=10000)

    @model_validator(mode="after")
    def safe_graph_audit(self):
        if self.include_quarantined and not self.include_untrusted:
            raise ValueError("include_quarantined requires include_untrusted")
        return self


class GraphManifestItem(RelationInput):
    client_request_id: str = Field(min_length=1, max_length=100)


class GraphDiffInput(Input):
    items: list[GraphManifestItem] = Field(min_length=1, max_length=100)
    scope_record_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=500
    )
    include_retract_candidates: bool = False

    @model_validator(mode="after")
    def unique_graph_manifest(self):
        request_ids = [item.client_request_id for item in self.items]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("client_request_id values must be unique")
        if len(self.scope_record_ids) != len(set(self.scope_record_ids)):
            raise ValueError("scope_record_ids must be unique")
        if self.include_retract_candidates and not self.scope_record_ids:
            raise ValueError("retract candidates require explicit scope_record_ids")
        return self


class GraphApplyInput(GraphDiffInput):
    approved_diff_hash: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    approved_create_client_ids: list[
        Annotated[str, Field(min_length=1, max_length=100)]
    ] = Field(default_factory=list, max_length=100)
    approved_retract_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=100
    )
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def explicit_graph_approval(self):
        for values in (self.approved_create_client_ids, self.approved_retract_ids):
            if len(values) != len(set(values)):
                raise ValueError("approved IDs must be unique")
        if not self.approved_create_client_ids and not self.approved_retract_ids:
            raise ValueError("at least one diff item must be explicitly approved")
        return self


class FeatureRequestInput(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    agent_name: str = Field(min_length=1, max_length=100)
    use_case: str = Field(default="", max_length=4000)
    priority: Literal["low", "medium", "high"] = "medium"
    source: str = Field(default="", max_length=2000)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=100)


class FeatureRequestUpdate(Input):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    use_case: str | None = Field(default=None, max_length=4000)
    priority: Literal["low", "medium", "high"] | None = None
    status: (
        Literal["received", "reviewing", "planned", "in_progress", "completed", "declined"] | None
    ) = None
    result: str | None = Field(default=None, max_length=10000)
    result_url: str | None = Field(default=None, max_length=2048)

    @field_validator("result_url")
    @classmethod
    def valid_result_url(cls, value):
        if value in (None, ""):
            return value
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError:
            raise ValueError("result_url must be a valid HTTP(S) URL") from None
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("result_url must be a public HTTP(S) URL without credentials")
        return value

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("at least one feature request field must be updated")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("feature request update fields cannot be null")
        return self


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
