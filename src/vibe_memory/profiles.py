"""Optional, agent-supplied metadata profiles.

These models validate representation only. They do not establish that a decision
was authorized or that a checkpoint result is true, independently verified, or
safe to execute.
"""

import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
LongText = Annotated[str, Field(min_length=1, max_length=4000)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{64}$")]

SENSITIVE_SETTING_PATTERN = re.compile(
    r"(?:authorization|cookie|credential|password|secret|token|api[_-]?key)", re.I
)


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileScope(ProfileInput):
    scope: ShortText
    project: ShortText | None = None
    environment: ShortText | None = None


class ProfileEvidence(ProfileInput):
    record_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    source_type: Literal[
        "git_commit",
        "requirements_revision",
        "document_revision",
        "web",
        "other",
    ] | None = None
    permalink: str | None = Field(default=None, min_length=1, max_length=2000)
    revision: str | None = Field(default=None, min_length=1, max_length=300)
    commit_sha: str | None = Field(
        default=None, min_length=7, max_length=64, pattern=r"^[0-9a-fA-F]+$"
    )
    observed_at: datetime | None = None

    @field_validator("commit_sha")
    @classmethod
    def normalize_commit_sha(cls, value):
        return value.lower() if value else value

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence observed_at must include a UTC offset")
        return value.astimezone(UTC)


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


class FailureSample(ProfileInput):
    identifier: ShortText
    record_id: str | None = Field(default=None, min_length=1, max_length=100)
    record_version: int | None = Field(default=None, ge=1)
    input_rows: int | None = Field(default=None, ge=0)
    input_bytes: int | None = Field(default=None, ge=0)
    description: LongText | None = None
    input_excerpt_redacted: LongText | None = None


class AttemptedSetting(ProfileInput):
    name: str = Field(min_length=1, max_length=100)
    value_redacted: str = Field(min_length=1, max_length=1000)

    @field_validator("name")
    @classmethod
    def reject_sensitive_setting_names(cls, value):
        if SENSITIVE_SETTING_PATTERN.search(value):
            raise ValueError("attempted setting names must not identify secrets or credentials")
        return value


class FailureDetail(ProfileInput):
    stage: ShortText
    code: ShortText | None = None
    message_redacted: LongText


class ParsingStep(ProfileInput):
    order: int = Field(ge=1, le=1000)
    stage: ShortText
    operation: ShortText
    input_summary: LongText
    output_summary: LongText


class MinimalReproduction(ProfileInput):
    conditions: list[LongText] = Field(min_length=1, max_length=30)
    command: LongText | None = None
    expected_result: LongText | None = None
    observed_result: LongText


class UploadedEvidenceReference(ProfileInput):
    kind: Literal["uploaded_file"]
    file_id: str = Field(min_length=1, max_length=100)
    file_version: int | None = Field(default=None, ge=1)


class ExternalReferenceVerification(ProfileInput):
    status: Literal["match", "changed", "missing", "inaccessible", "unverified"]
    checked_at: datetime | None = None
    observed_sha256: Sha256 | None = None
    observed_bytes: int | None = Field(default=None, ge=0)
    detail_redacted: LongText | None = None

    @field_validator("checked_at")
    @classmethod
    def normalize_checked_at(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checked_at must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_status_coordinates(self):
        observed = self.observed_sha256 is not None or self.observed_bytes is not None
        if self.status == "unverified":
            if self.checked_at is not None or observed:
                raise ValueError("unverified references cannot include check results")
        elif self.checked_at is None:
            raise ValueError("verified reference states require checked_at")
        if self.status in {"missing", "inaccessible"} and observed:
            raise ValueError(f"{self.status} references cannot include observed content coordinates")
        return self


class ExternalEvidenceReference(ProfileInput):
    kind: Literal["external"]
    reference: str = Field(min_length=1, max_length=2000)
    expected_sha256: Sha256 | None = None
    expected_bytes: int | None = Field(default=None, ge=0)
    verification: ExternalReferenceVerification = Field(
        default_factory=lambda: ExternalReferenceVerification(status="unverified")
    )

    @model_validator(mode="after")
    def validate_comparison(self):
        status = self.verification.status
        hash_pair = self.expected_sha256 is not None and self.verification.observed_sha256 is not None
        size_pair = self.expected_bytes is not None and self.verification.observed_bytes is not None
        if status in {"match", "changed"} and not (hash_pair or size_pair):
            raise ValueError(f"{status} requires comparable expected and observed coordinates")
        comparisons = []
        if hash_pair:
            comparisons.append(
                self.expected_sha256.casefold() == self.verification.observed_sha256.casefold()
            )
        if size_pair:
            comparisons.append(self.expected_bytes == self.verification.observed_bytes)
        if status == "match" and comparisons and not all(comparisons):
            raise ValueError("match coordinates must be equal")
        if status == "changed" and comparisons and all(comparisons):
            raise ValueError("changed requires at least one different coordinate")
        return self


EvidenceReference = Annotated[
    UploadedEvidenceReference | ExternalEvidenceReference,
    Field(discriminator="kind"),
]


class FailureReproductionProfile(ProfileInput):
    type: Literal["failure_reproduction"]
    version: Literal[1]
    outcome: Literal["failed", "invalid_result"]
    observed_at: datetime
    sample: FailureSample
    attempted_settings: list[AttemptedSetting] = Field(default_factory=list, max_length=30)
    failure: FailureDetail
    minimal_reproduction: MinimalReproduction
    parsing_steps: list[ParsingStep] = Field(default_factory=list, max_length=100)
    evidence_references: list[EvidenceReference] = Field(default_factory=list, max_length=50)

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_parsing_order(self):
        orders = [step.order for step in self.parsing_steps]
        if orders != sorted(orders) or len(orders) != len(set(orders)):
            raise ValueError("parsing step order values must be unique and ascending")
        return self


class ImpactReviewTarget(ProfileInput):
    kind: Literal["record", "relation"]
    id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)


class EvidenceImpactReviewProfile(ProfileInput):
    """One reviewer observation; conflicting observations remain separate records."""

    type: Literal["evidence_impact_review"]
    version: Literal[1]
    target: ImpactReviewTarget
    evidence: ProfileEvidence
    reviewer: ShortText
    observed_at: datetime
    impact: Literal["affected", "not_affected", "unknown"]
    rationale: LongText
    follow_up: list[LongText] = Field(default_factory=list, max_length=30)

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset")
        return value.astimezone(UTC)


class HarnessReference(ProfileInput):
    """Agent-reported harness coordinates; authenticated writer identity is separate."""

    id: ShortText
    version: ShortText | None = None


class SkillReference(ProfileInput):
    id: ShortText
    version: ShortText | None = None
    digest: str | None = Field(
        default=None,
        pattern=r"^(?:sha256:)?[0-9a-fA-F]{64}$",
        max_length=71,
    )

    @field_validator("digest")
    @classmethod
    def normalize_digest(cls, value):
        return value.lower() if value else value

    @model_validator(mode="after")
    def versioned_reference(self):
        if self.version is None and self.digest is None:
            raise ValueError("skill references require version or digest")
        return self


class AgentStateProfile(ProfileInput):
    """Harness-neutral task state supplied by an external agent."""

    type: Literal["agent_state"]
    version: Literal[1]
    project_id: ShortText
    task_id: ShortText
    state_version: int = Field(ge=1)
    status: Literal[
        "unknown",
        "planned",
        "in_progress",
        "blocked",
        "completed",
        "cancelled",
    ]
    goal: LongText
    completed: list[LongText] = Field(default_factory=list, max_length=50)
    next_actions: list[LongText] = Field(default_factory=list, max_length=50)
    blockers: list[LongText] = Field(default_factory=list, max_length=30)
    decision_refs: list[ProfileEvidence] = Field(default_factory=list, max_length=50)
    evidence_refs: list[ProfileEvidence] = Field(default_factory=list, max_length=50)
    skill_refs: list[SkillReference] = Field(default_factory=list, max_length=50)
    reported_harness: HarnessReference
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset")
        return value.astimezone(UTC)


class SkillExecutionProfile(ProfileInput):
    """A reported Skill execution observation; it never authorizes execution."""

    type: Literal["skill_execution"]
    version: Literal[1]
    skill: SkillReference
    reported_harness: HarnessReference
    reported_agent: ShortText | None = None
    task_ref: ProfileEvidence | None = None
    environment_ref: ProfileEvidence | None = None
    input_refs: list[ProfileEvidence] = Field(default_factory=list, max_length=50)
    started_at: datetime
    finished_at: datetime | None = None
    reported_status: Literal["started", "succeeded", "failed", "cancelled", "unknown"]
    evidence_refs: list[ProfileEvidence] = Field(default_factory=list, max_length=50)
    artifact_refs: list[ProfileEvidence] = Field(default_factory=list, max_length=50)
    failure_reason: LongText | None = None
    verification_status: Literal[
        "unverified",
        "author_reported",
        "observed",
        "reproduced",
        "unavailable",
    ]

    @field_validator("started_at", "finished_at")
    @classmethod
    def normalize_execution_time(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("execution timestamps must include a UTC offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def terminal_coordinates(self):
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at must not be earlier than started_at")
        if self.reported_status != "started" and self.finished_at is None:
            raise ValueError("terminal or unknown execution status requires finished_at")
        if self.reported_status == "failed" and not self.failure_reason:
            raise ValueError("failed Skill executions require failure_reason")
        return self


def agent_state_summary(metadata: dict) -> dict | None:
    profile = (metadata or {}).get("vibe_memory_agent_state")
    if not isinstance(profile, dict) or profile.get("type") != "agent_state":
        return None
    harness = profile.get("reported_harness") or {}
    return {
        "profile_version": profile.get("version"),
        "project_id": profile.get("project_id"),
        "task_id": profile.get("task_id"),
        "state_version": profile.get("state_version"),
        "status": profile.get("status"),
        "reported_harness": harness.get("id") if isinstance(harness, dict) else None,
    }


def skill_execution_summary(metadata: dict) -> dict | None:
    profile = (metadata or {}).get("vibe_memory_skill_execution")
    if not isinstance(profile, dict) or profile.get("type") != "skill_execution":
        return None
    skill = profile.get("skill") or {}
    harness = profile.get("reported_harness") or {}
    return {
        "profile_version": profile.get("version"),
        "skill_id": skill.get("id") if isinstance(skill, dict) else None,
        "skill_version": skill.get("version") if isinstance(skill, dict) else None,
        "reported_status": profile.get("reported_status"),
        "verification_status": profile.get("verification_status"),
        "reported_harness": harness.get("id") if isinstance(harness, dict) else None,
    }


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

    failure_key = "vibe_memory_failure_reproduction"
    raw_failure = normalized.get(failure_key)
    failure_mirrors = (
        "vibe_memory_failure_profile_version",
        "vibe_memory_failure_outcome",
        "vibe_memory_failure_stage",
        "vibe_memory_failure_reference_status",
    )
    if raw_failure is None:
        for key in failure_mirrors:
            normalized.pop(key, None)
    else:
        if not isinstance(raw_failure, dict):
            raise ValueError(f"{failure_key} must be an object")
        profile = FailureReproductionProfile.model_validate(raw_failure)
        external_statuses = {
            reference.verification.status
            for reference in profile.evidence_references
            if isinstance(reference, ExternalEvidenceReference)
        }
        reference_status = (
            "none"
            if not external_statuses
            else next(iter(external_statuses))
            if len(external_statuses) == 1
            else "mixed"
        )
        normalized[failure_key] = profile.model_dump(mode="json", exclude_none=True)
        normalized["vibe_memory_failure_profile_version"] = profile.version
        normalized["vibe_memory_failure_outcome"] = profile.outcome
        normalized["vibe_memory_failure_stage"] = profile.failure.stage
        normalized["vibe_memory_failure_reference_status"] = reference_status

    impact_key = "vibe_memory_evidence_impact_review"
    raw_impact = normalized.get(impact_key)
    impact_mirrors = (
        "vibe_memory_evidence_impact_profile_version",
        "vibe_memory_evidence_impact",
        "vibe_memory_evidence_impact_target_kind",
    )
    if raw_impact is None:
        for key in impact_mirrors:
            normalized.pop(key, None)
    else:
        if not isinstance(raw_impact, dict):
            raise ValueError(f"{impact_key} must be an object")
        impact = EvidenceImpactReviewProfile.model_validate(raw_impact)
        normalized[impact_key] = impact.model_dump(mode="json", exclude_none=True)
        normalized["vibe_memory_evidence_impact_profile_version"] = impact.version
        normalized["vibe_memory_evidence_impact"] = impact.impact
        normalized["vibe_memory_evidence_impact_target_kind"] = impact.target.kind

    state_key = "vibe_memory_agent_state"
    raw_state = normalized.get(state_key)
    state_mirrors = (
        "vibe_memory_agent_state_profile_version",
        "vibe_memory_agent_state_project_id",
        "vibe_memory_agent_state_task_id",
        "vibe_memory_agent_state_status",
        "vibe_memory_agent_state_version",
        "vibe_memory_agent_state_harness",
    )
    if raw_state is None:
        for key in state_mirrors:
            normalized.pop(key, None)
    else:
        if not isinstance(raw_state, dict):
            raise ValueError(f"{state_key} must be an object")
        state = AgentStateProfile.model_validate(raw_state)
        normalized[state_key] = state.model_dump(mode="json", exclude_none=True)
        normalized["vibe_memory_agent_state_profile_version"] = state.version
        normalized["vibe_memory_agent_state_project_id"] = state.project_id
        normalized["vibe_memory_agent_state_task_id"] = state.task_id
        normalized["vibe_memory_agent_state_status"] = state.status
        normalized["vibe_memory_agent_state_version"] = state.state_version
        normalized["vibe_memory_agent_state_harness"] = state.reported_harness.id

    execution_key = "vibe_memory_skill_execution"
    raw_execution = normalized.get(execution_key)
    execution_mirrors = (
        "vibe_memory_skill_execution_profile_version",
        "vibe_memory_skill_id",
        "vibe_memory_skill_execution_status",
        "vibe_memory_skill_verification_status",
        "vibe_memory_skill_execution_harness",
    )
    if raw_execution is None:
        for key in execution_mirrors:
            normalized.pop(key, None)
    else:
        if not isinstance(raw_execution, dict):
            raise ValueError(f"{execution_key} must be an object")
        execution = SkillExecutionProfile.model_validate(raw_execution)
        normalized[execution_key] = execution.model_dump(mode="json", exclude_none=True)
        normalized["vibe_memory_skill_execution_profile_version"] = execution.version
        normalized["vibe_memory_skill_id"] = execution.skill.id
        normalized["vibe_memory_skill_execution_status"] = execution.reported_status
        normalized["vibe_memory_skill_verification_status"] = execution.verification_status
        normalized["vibe_memory_skill_execution_harness"] = execution.reported_harness.id
    if len(json.dumps(normalized, ensure_ascii=False, allow_nan=False)) > 30000:
        raise ValueError("metadata must fit within 30000 characters of JSON")
    return normalized
