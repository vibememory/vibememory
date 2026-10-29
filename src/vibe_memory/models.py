from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class RecordInput(KeywordsInput):
    source: str = Field(default="", max_length=2000)
    tags: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=30
    )
    metadata: dict = Field(default_factory=dict)

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


class VaultInput(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    value: str = Field(min_length=1, max_length=65536)
    description: str = Field(default="", max_length=500)


class SearchInput(KeywordsInput):
    limit: int = Field(default=8, ge=1, le=50)
    scope: Literal["all", "memories", "documents", "entities"] = "all"
    tags: list[str] = Field(default_factory=list, max_length=30)


class FeatureRequestInput(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    agent_name: str = Field(min_length=1, max_length=100)
    use_case: str = Field(default="", max_length=4000)
    priority: Literal["low", "medium", "high"] = "medium"
    source: str = Field(default="", max_length=2000)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=100)
