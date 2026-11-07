"""Optional, agent-supplied metadata profiles.

These models validate representation only. They do not establish that a decision
was authorized or that a checkpoint result is true, independently verified, or
safe to execute.
"""

import json
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
LongText = Annotated[str, Field(min_length=1, max_length=4000)]


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileScope(ProfileInput):
    scope: ShortText
    project: ShortText | None = None
    environment: ShortText | None = None


class ProfileEvidence(ProfileInput):
    record_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)


class DecisionProfile(ProfileInput):
    type: Literal["decision"]
    version: Literal[1]
    state: Literal["proposed", "open", "decided", "rejected", "unknown"]
    topic: ShortText
    option: ShortText | None = None
    applies_to: ProfileScope
    reported_decider: ShortText | None = None
    decided_at: datetime | None = None
    evidence: list[ProfileEvidence] = Field(default_factory=list, max_length=50)
    reason: LongText | None = None
    reconsider_when: list[LongText] = Field(default_factory=list, max_length=20)

    @field_validator("decided_at")
    @classmethod
    def normalize_decided_at(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decided_at must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_terminal_state_coordinates(self):
        if self.state in {"decided", "rejected"}:
            if not self.reported_decider:
                raise ValueError("decided and rejected profiles require reported_decider")
            if self.decided_at is None:
                raise ValueError("decided and rejected profiles require decided_at")
            if not self.evidence:
                raise ValueError("decided and rejected profiles require evidence")
        if self.state == "rejected" and not self.reason:
            raise ValueError("rejected profiles require reason")
        return self


class Reproduction(ProfileInput):
    command: str = Field(min_length=1, max_length=4000)
    reported_result: str = Field(min_length=1, max_length=4000)


class CheckpointProfile(ProfileInput):
    type: Literal["checkpoint"]
    version: Literal[1]
    claimed_stage: Literal[
        "unknown",
        "planned",
        "implemented",
        "local_tests_passed",
        "merged",
        "deployed",
        "operationally_verified",
    ]
    observation_kind: Literal[
        "author_reported", "observed", "reproduced", "failed", "unavailable"
    ]
    target: ProfileScope
    observed_at: datetime
    commit: str | None = Field(default=None, min_length=1, max_length=200)
    artifact_digest: str | None = Field(default=None, min_length=1, max_length=300)
    environment_identity: str | None = Field(default=None, min_length=1, max_length=1000)
    lockfile_digest: str | None = Field(default=None, min_length=1, max_length=300)
    reproduction: Reproduction | None = None
    reported_result: str | None = Field(default=None, min_length=1, max_length=4000)
    evidence: list[ProfileEvidence] = Field(default_factory=list, max_length=50)
    remaining_unknowns: list[LongText] = Field(default_factory=list, max_length=30)

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset")
        return value.astimezone(UTC)


def normalize_metadata_profiles(metadata: dict) -> dict:
    """Validate an opted-in profile and add deterministic scalar filter mirrors."""

    normalized = dict(metadata)
    raw_profile = normalized.get("vibe_memory_profile")
    if raw_profile is not None:
        if not isinstance(raw_profile, dict):
            raise ValueError("vibe_memory_profile must be an object")
        profile_type = raw_profile.get("type")
        version = raw_profile.get("version")
        if version != 1:
            raise ValueError("vibe_memory_profile version must be 1")
        if profile_type == "decision":
            profile = DecisionProfile.model_validate(raw_profile)
            state = profile.state
            normalized.pop("vibe_memory_profile_observation", None)
        elif profile_type == "checkpoint":
            profile = CheckpointProfile.model_validate(raw_profile)
            state = profile.claimed_stage
            normalized["vibe_memory_profile_observation"] = profile.observation_kind
        else:
            raise ValueError("vibe_memory_profile type must be decision or checkpoint")
        normalized["vibe_memory_profile"] = profile.model_dump(mode="json", exclude_none=True)
        normalized["vibe_memory_profile_type"] = profile_type
        normalized["vibe_memory_profile_version"] = version
        normalized["vibe_memory_profile_state"] = state
    if len(json.dumps(normalized, ensure_ascii=False, allow_nan=False)) > 30000:
        raise ValueError("metadata must fit within 30000 characters of JSON")
    return normalized
