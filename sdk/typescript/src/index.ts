export type SearchMode = "exact" | "semantic" | "hybrid";
export type RetrievalProjection = "minimal" | "standard";
export type SearchRetrievalOptions = {
  projection?: RetrievalProjection;
  byte_limit?: number;
  limit?: number;
};
export type ProfileScope = {scope: string; project?: string; environment?: string};
export type ProfileEvidence = {
  record_id: string;
  version: number;
  source_type?: "git_commit" | "requirements_revision" | "document_revision" | "web" | "other";
  permalink?: string;
  revision?: string;
  commit_sha?: string;
  observed_at?: string;
};
export type DecisionProfile = {
  type: "decision";
  version: 1;
  state: "proposed" | "open" | "decided" | "rejected" | "unknown";
  topic: string;
  option?: string;
  applies_to: ProfileScope;
  reported_decider?: string;
  decided_at?: string;
  evidence?: ProfileEvidence[];
  reason?: string;
  reconsider_when?: string[];
};
export type CheckpointProfile = {
  type: "checkpoint";
  version: 1;
  claimed_stage: "unknown" | "planned" | "implemented" | "local_tests_passed" | "merged" | "deployed" | "operationally_verified";
  observation_kind: "author_reported" | "observed" | "reproduced" | "failed" | "unavailable";
  target: ProfileScope;
  observed_at: string;
  commit?: string;
  artifact_digest?: string;
  environment_identity?: string;
  lockfile_digest?: string;
  reproduction?: {command: string; reported_result: string};
  reported_result?: string;
  evidence?: ProfileEvidence[];
  remaining_unknowns?: string[];
};
export type FailureSample = {
  identifier: string;
  record_id?: string;
  record_version?: number;
  input_rows?: number;
  input_bytes?: number;
  description?: string;
  input_excerpt_redacted?: string;
};
export type ExternalReferenceStatus =
  | "match"
  | "changed"
  | "missing"
  | "inaccessible"
  | "unverified";
export type FailureEvidenceReference =
  | {kind: "uploaded_file"; file_id: string; file_version?: number}
  | {
      kind: "external";
      reference: string;
      expected_sha256?: string;
      expected_bytes?: number;
      verification?: {
        status: ExternalReferenceStatus;
        checked_at?: string;
        observed_sha256?: string;
        observed_bytes?: number;
        detail_redacted?: string;
      };
    };
export type FailureReproductionProfile = {
  type: "failure_reproduction";
  version: 1;
  outcome: "failed" | "invalid_result";
  observed_at: string;
  sample: FailureSample;
  attempted_settings?: Array<{name: string; value_redacted: string}>;
  failure: {stage: string; code?: string; message_redacted: string};
  minimal_reproduction: {
    conditions: string[];
    command?: string;
    expected_result?: string;
    observed_result: string;
  };
  parsing_steps?: Array<{
    order: number;
    stage: string;
    operation: string;
    input_summary: string;
    output_summary: string;
  }>;
  evidence_references?: FailureEvidenceReference[];
};
export type EvidenceImpactReviewProfile = {
  type: "evidence_impact_review";
  version: 1;
  target: {kind: "record" | "relation"; id: string; version: number};
  evidence: ProfileEvidence;
  reviewer: string;
  observed_at: string;
  impact: "affected" | "not_affected" | "unknown";
  rationale: string;
  follow_up?: string[];
};
export type EvidenceImpactReviewMetadata = Record<string, unknown> & {
  vibe_memory_evidence_impact_review: EvidenceImpactReviewProfile;
  vibe_memory_evidence_impact_profile_version: 1;
  vibe_memory_evidence_impact: EvidenceImpactReviewProfile["impact"];
  vibe_memory_evidence_impact_target_kind: EvidenceImpactReviewProfile["target"]["kind"];
};
export type HarnessReference = {id: string; version?: string};
export type SkillReference = {id: string; version?: string; digest?: string};
export type AgentStateProfile = {
  type: "agent_state";
  version: 1;
  project_id: string;
  task_id: string;
  state_version: number;
  status: "unknown" | "planned" | "in_progress" | "blocked" | "completed" | "cancelled";
  goal: string;
  completed?: string[];
  next_actions?: string[];
  blockers?: string[];
  decision_refs?: ProfileEvidence[];
  evidence_refs?: ProfileEvidence[];
  skill_refs?: SkillReference[];
  reported_harness: HarnessReference;
  observed_at: string;
};
export type AgentStateMetadata = Record<string, unknown> & {
  vibe_memory_agent_state: AgentStateProfile;
  vibe_memory_agent_state_profile_version: 1;
  vibe_memory_agent_state_project_id: string;
  vibe_memory_agent_state_task_id: string;
  vibe_memory_agent_state_status: AgentStateProfile["status"];
  vibe_memory_agent_state_version: number;
  vibe_memory_agent_state_harness: string;
};
export type SkillExecutionProfile = {
  type: "skill_execution";
  version: 1;
  skill: SkillReference;
  reported_harness: HarnessReference;
  reported_agent?: string;
  task_ref?: ProfileEvidence;
  environment_ref?: ProfileEvidence;
  input_refs?: ProfileEvidence[];
  started_at: string;
  finished_at?: string;
  reported_status: "started" | "succeeded" | "failed" | "cancelled" | "unknown";
  evidence_refs?: ProfileEvidence[];
  artifact_refs?: ProfileEvidence[];
  failure_reason?: string;
  verification_status: "unverified" | "author_reported" | "observed" | "reproduced" | "unavailable";
};
export type SkillExecutionMetadata = Record<string, unknown> & {
  vibe_memory_skill_execution: SkillExecutionProfile;
  vibe_memory_skill_execution_profile_version: 1;
  vibe_memory_skill_id: string;
  vibe_memory_skill_execution_status: SkillExecutionProfile["reported_status"];
  vibe_memory_skill_verification_status: SkillExecutionProfile["verification_status"];
  vibe_memory_skill_execution_harness: string;
};
export type RecordCoordinate = {record_id: string; version: number};
export type StateReconciliationProfile = {
  type: "state_reconciliation";
  version: 1;
  project_id: string;
  task_id: string;
  status: "open" | "resolved";
  candidate_refs: RecordCoordinate[];
  selected_ref?: RecordCoordinate;
  reported_resolver?: string;
  rationale?: string;
  observed_at: string;
  resolved_at?: string;
};
export type AgentCapabilityManifestProfile = {
  type: "agent_capability_manifest";
  version: 1;
  manifest_version: number;
  agent_id: string;
  harness: HarnessReference;
  capabilities: string[];
  skill_refs?: SkillReference[];
  supported_task_types?: string[];
  required_permissions?: string[];
  observed_at: string;
};
export type ContextLifecycleProfile = {
  type: "context_lifecycle";
  version: 1;
  context_class: "ephemeral_execution" | "session" | "project" | "long_term" | "decision_history" | "archived_context";
  retention: "indefinite" | "manual_archive" | "until";
  expires_at?: string;
  context_bundle_policy: "include" | "explicit_only" | "exclude";
  reason?: string;
  observed_at: string;
};
export type FailureReproductionMetadata = Record<string, unknown> & {
  vibe_memory_failure_reproduction: FailureReproductionProfile;
  vibe_memory_failure_profile_version: 1;
  vibe_memory_failure_outcome: FailureReproductionProfile["outcome"];
  vibe_memory_failure_stage: string;
  vibe_memory_failure_reference_status: ExternalReferenceStatus | "none" | "mixed";
};
export type ProfileMetadata = Record<string, unknown> & {
  vibe_memory_profile: DecisionProfile | CheckpointProfile;
  vibe_memory_profile_type: "decision" | "checkpoint";
  vibe_memory_profile_version: 1;
  vibe_memory_profile_state: string;
  vibe_memory_profile_observation?: CheckpointProfile["observation_kind"];
};

/** Builds agent-supplied metadata; this does not establish truth, authority, or approval. */
export function decisionProfileMetadata(
  profile: Omit<DecisionProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
): ProfileMetadata {
  return {
    ...metadata,
    vibe_memory_profile: {...profile, type: "decision", version: 1},
    vibe_memory_profile_type: "decision",
    vibe_memory_profile_version: 1,
    vibe_memory_profile_state: profile.state,
  };
}

/** Builds data-only checkpoint metadata; stored commands are never run by Vibe Memory. */
export function checkpointProfileMetadata(
  profile: Omit<CheckpointProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
): ProfileMetadata {
  return {
    ...metadata,
    vibe_memory_profile: {...profile, type: "checkpoint", version: 1},
    vibe_memory_profile_type: "checkpoint",
    vibe_memory_profile_version: 1,
    vibe_memory_profile_state: profile.claimed_stage,
    vibe_memory_profile_observation: profile.observation_kind,
  };
}

/** Builds sanitized failure evidence; this helper never opens external references. */
export function failureReproductionProfileMetadata(
  profile: Omit<FailureReproductionProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
): FailureReproductionMetadata {
  const externalStatuses = new Set(
    (profile.evidence_references ?? [])
      .filter((reference): reference is Extract<FailureEvidenceReference, {kind: "external"}> =>
        reference.kind === "external",
      )
      .map((reference) => reference.verification?.status ?? "unverified"),
  );
  const referenceStatus =
    externalStatuses.size === 0
      ? "none"
      : externalStatuses.size === 1
        ? [...externalStatuses][0]
        : "mixed";
  return {
    ...metadata,
    vibe_memory_failure_reproduction: {...profile, type: "failure_reproduction", version: 1},
    vibe_memory_failure_profile_version: 1,
    vibe_memory_failure_outcome: profile.outcome,
    vibe_memory_failure_stage: profile.failure.stage,
    vibe_memory_failure_reference_status: referenceStatus,
  };
}

/** Builds one evidence-impact observation; conflicting reviewers remain separate records. */
export function evidenceImpactReviewProfileMetadata(
  profile: Omit<EvidenceImpactReviewProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
): EvidenceImpactReviewMetadata {
  return {
    ...metadata,
    vibe_memory_evidence_impact_review: {
      ...profile,
      type: "evidence_impact_review",
      version: 1,
    },
    vibe_memory_evidence_impact_profile_version: 1,
    vibe_memory_evidence_impact: profile.impact,
    vibe_memory_evidence_impact_target_kind: profile.target.kind,
  };
}

/** Builds harness-neutral task state. Record version remains the conflict coordinate. */
export function agentStateProfileMetadata(
  profile: Omit<AgentStateProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
): AgentStateMetadata {
  return {
    ...metadata,
    vibe_memory_agent_state: {...profile, type: "agent_state", version: 1},
    vibe_memory_agent_state_profile_version: 1,
    vibe_memory_agent_state_project_id: profile.project_id,
    vibe_memory_agent_state_task_id: profile.task_id,
    vibe_memory_agent_state_status: profile.status,
    vibe_memory_agent_state_version: profile.state_version,
    vibe_memory_agent_state_harness: profile.reported_harness.id,
  };
}

/** Builds an external harness execution observation. Vibe Memory executes nothing. */
export function skillExecutionProfileMetadata(
  profile: Omit<SkillExecutionProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
): SkillExecutionMetadata {
  return {
    ...metadata,
    vibe_memory_skill_execution: {...profile, type: "skill_execution", version: 1},
    vibe_memory_skill_execution_profile_version: 1,
    vibe_memory_skill_id: profile.skill.id,
    vibe_memory_skill_execution_status: profile.reported_status,
    vibe_memory_skill_verification_status: profile.verification_status,
    vibe_memory_skill_execution_harness: profile.reported_harness.id,
  };
}

/** Records an explicit external resolution without semantically merging competing state. */
export function stateReconciliationProfileMetadata(
  profile: Omit<StateReconciliationProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
) {
  return {
    ...metadata,
    vibe_memory_state_reconciliation: {...profile, type: "state_reconciliation", version: 1},
    vibe_memory_state_reconciliation_profile_version: 1,
    vibe_memory_state_reconciliation_project_id: profile.project_id,
    vibe_memory_state_reconciliation_task_id: profile.task_id,
    vibe_memory_state_reconciliation_status: profile.status,
  };
}

/** Records declared capabilities without granting permissions or assigning work. */
export function agentCapabilityManifestProfileMetadata(
  profile: Omit<AgentCapabilityManifestProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
) {
  return {
    ...metadata,
    vibe_memory_agent_capability_manifest: {
      ...profile,
      type: "agent_capability_manifest",
      version: 1,
    },
    vibe_memory_agent_capability_profile_version: 1,
    vibe_memory_agent_capability_manifest_version: profile.manifest_version,
    vibe_memory_agent_capability_agent_id: profile.agent_id,
    vibe_memory_agent_capability_harness: profile.harness.id,
  };
}

/** Records lifecycle intent without deleting, archiving, or broadening access. */
export function contextLifecycleProfileMetadata(
  profile: Omit<ContextLifecycleProfile, "type" | "version">,
  metadata: Record<string, unknown> = {},
) {
  return {
    ...metadata,
    vibe_memory_context_lifecycle: {...profile, type: "context_lifecycle", version: 1},
    vibe_memory_context_lifecycle_profile_version: 1,
    vibe_memory_context_class: profile.context_class,
    vibe_memory_context_retention: profile.retention,
    vibe_memory_context_bundle_policy: profile.context_bundle_policy,
    ...(profile.expires_at ? {vibe_memory_context_expires_at: profile.expires_at} : {}),
  };
}

export type Memory = {
  id: string;
  kind: "memory";
  content: string;
  keywords: string[];
  version: number;
  created_at: string;
  metadata: Record<string, unknown>;
  correction_status?: string;
};
export type SearchHit = {
  id: string;
  kind: string;
  title: string;
  keywords: string[];
  score: number;
  matched_keywords: Array<{
    query_keyword: string;
    stored_keyword: string;
    similarity: number;
  }>;
  trust_level: string;
  security_state: string;
  correction_status?: string;
  correction_graph_complete?: boolean;
  metadata?: Record<string, unknown>;
  agent_state?: {
    profile_version: number;
    project_id: string;
    task_id: string;
    state_version: number;
    status: AgentStateProfile["status"];
    reported_harness: string;
  };
  skill_execution?: {
    profile_version: number;
    skill_id: string;
    skill_version?: string;
    reported_status: SkillExecutionProfile["reported_status"];
    verification_status: SkillExecutionProfile["verification_status"];
    reported_harness: string;
  };
  state_reconciliation?: {
    profile_version: number;
    project_id: string;
    task_id: string;
    status: StateReconciliationProfile["status"];
    candidate_count: number;
  };
  agent_capability_manifest?: {
    profile_version: number;
    manifest_version: number;
    agent_id: string;
    harness: string;
    capability_count: number;
  };
  context_lifecycle?: {
    profile_version: number;
    context_class: ContextLifecycleProfile["context_class"];
    retention: ContextLifecycleProfile["retention"];
    expires_at?: string;
    context_bundle_policy: ContextLifecycleProfile["context_bundle_policy"];
  };
};
export type SearchResponse = {
  mode: "keyword_vector";
  match_mode: SearchMode;
  projection: RetrievalProjection;
  byte_limit: number;
  response_bytes: number;
  selected_hits: number;
  returned: number;
  truncated: boolean;
  hits: SearchHit[];
};
export type Page<T> = {items: T[]; limit: number; offset: number};
export type BatchItem<T = unknown> = {
  index: number;
  client_request_id: string;
  status: "created" | "updated" | "existing" | "conflict" | "failed";
  id?: string;
  version?: number;
  resource?: T;
  error?: {code: string; message: string; retryable: boolean};
};
export type BatchResult<T = unknown> = {
  items: Array<BatchItem<T>>;
  counts: Record<string, number>;
  total: number;
  atomic: false;
};
export type RequestOptions = {signal?: AbortSignal; timeoutMs?: number};

type ErrorContract = {
  reason_code?: string;
  retryable?: boolean;
  request_id?: string;
};

export class VibeMemoryError extends Error {
  readonly code?: string;
  readonly retryable: boolean;
  readonly requestId?: string;

  constructor(
    readonly status: number,
    readonly body: string,
    contract: ErrorContract = {},
  ) {
    super(`Vibe Memory ${status}: ${contract.reason_code ?? body}`);
    this.name = "VibeMemoryError";
    this.code = contract.reason_code;
    this.retryable = Boolean(contract.retryable);
    this.requestId = contract.request_id;
  }
}

export class VibeMemoryClient {
  constructor(
    private baseUrl: string,
    private token: string,
    private namespace = "default",
    private contractVersion = "1.1",
  ) {}

  private async request<T>(
    path: string,
    init: RequestInit = {},
    retry = false,
    options: RequestOptions = {},
  ): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort("timeout"), options.timeoutMs ?? 20_000);
    const cancel = () => controller.abort(options.signal?.reason);
    if (options.signal?.aborted) cancel();
    else options.signal?.addEventListener("abort", cancel, {once: true});
    try {
      const response = await fetch(new URL(path, this.baseUrl), {
        ...init,
        signal: controller.signal,
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${this.token}`,
          "x-vibe-memory-namespace": this.namespace,
          "vibe-memory-contract-version": this.contractVersion,
          ...init.headers,
        },
      });
      if (response.status === 429 && retry) {
        const delay = Math.min(Number(response.headers.get("retry-after") || 1), 30);
        await new Promise<void>((resolve, reject) => {
          const retryTimer = setTimeout(resolve, Math.max(delay, 0) * 1000);
          controller.signal.addEventListener(
            "abort",
            () => {
              clearTimeout(retryTimer);
              reject(controller.signal.reason);
            },
            {once: true},
          );
        });
        return this.request<T>(path, init, false, options);
      }
      if (!response.ok) {
        const body = await response.text();
        let contract: ErrorContract = {};
        try {
          contract = (JSON.parse(body) as {error?: ErrorContract}).error ?? {};
        } catch {
          // Non-JSON gateways remain visible through the raw body.
        }
        throw new VibeMemoryError(response.status, body, contract);
      }
      return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
    } finally {
      clearTimeout(timeout);
      options.signal?.removeEventListener("abort", cancel);
    }
  }

  get(id: string, options: RequestOptions = {}) {
    return this.request<Memory>(`/v1/records/${encodeURIComponent(id)}`, {}, false, options);
  }

  search(
    keywords: string[],
    match_mode: SearchMode = "hybrid",
    options: RequestOptions = {},
    retrieval: SearchRetrievalOptions = {},
  ) {
    return this.request<SearchResponse>(
      "/v1/search",
      {
        method: "POST",
        body: JSON.stringify({
          keywords,
          match_mode,
          projection: retrieval.projection ?? "minimal",
          byte_limit: retrieval.byte_limit ?? 16384,
          limit: retrieval.limit ?? 8,
        }),
      },
      true,
      options,
    );
  }

  create(
    content: string,
    keywords: string[],
    client_request_id?: string,
    options: RequestOptions = {},
  ) {
    return this.request<Memory>(
      "/v1/memories",
      {method: "POST", body: JSON.stringify({content, keywords, kind: "fact", client_request_id})},
      Boolean(client_request_id),
      options,
    );
  }

  createWithMetadata(
    content: string,
    keywords: string[],
    metadata: Record<string, unknown>,
    client_request_id?: string,
    options: RequestOptions = {},
  ) {
    return this.request<Memory>(
      "/v1/memories",
      {method: "POST", body: JSON.stringify({content, keywords, kind: "fact", metadata, client_request_id})},
      Boolean(client_request_id),
      options,
    );
  }

  correct(
    previous_id: string,
    expected_previous_version: number,
    replacement: {content: string; keywords: string[]},
    reason: string,
    client_request_id: string,
    options: RequestOptions = {},
  ) {
    return this.request(
      "/v1/corrections/memories",
      {
        method: "POST",
        body: JSON.stringify({
          previous_id,
          expected_previous_version,
          replacement: {...replacement, kind: "fact"},
          relation: "CORRECTS",
          correction_scope: "full",
          reason,
          client_request_id,
        }),
      },
      true,
      options,
    );
  }

  list(limit = 50, offset = 0, options: RequestOptions = {}) {
    return this.request<Page<Memory>>(`/v1/records?limit=${limit}&offset=${offset}`, {}, false, options);
  }

  async *records(limit = 50, offset = 0, options: RequestOptions = {}) {
    while (true) {
      const page = await this.list(limit, offset, options);
      yield page;
      if (page.items.length < limit) return;
      offset += page.items.length;
    }
  }

  createEntities(items: Array<Record<string, unknown>>, options: RequestOptions = {}) {
    return this.request<BatchResult>(
      "/v1/entities/batch",
      {method: "POST", body: JSON.stringify({items, return: "minimal", atomic: false})},
      false,
      options,
    );
  }

  contextBundle(request: Record<string, unknown>, options: RequestOptions = {}) {
    return this.request(
      "/v1/context-bundle",
      {
        method: "POST",
        body: JSON.stringify({projection: "minimal", byte_limit: 32768, ...request}),
      },
      true,
      options,
    );
  }

  evidenceImpactCandidates(
    evidence_record_id: string,
    evidence_version: number,
    candidate_limit = 100,
    options: RequestOptions = {},
  ) {
    return this.request(
      "/v1/evidence-impact/candidates",
      {
        method: "POST",
        body: JSON.stringify({evidence_record_id, evidence_version, candidate_limit}),
      },
      false,
      options,
    );
  }

  stateReconciliationCandidates(
    project_id: string,
    task_id: string,
    candidate_limit = 100,
    options: RequestOptions = {},
  ) {
    return this.request(
      "/v1/agent-states/reconciliation/candidates",
      {
        method: "POST",
        body: JSON.stringify({project_id, task_id, candidate_limit}),
      },
      false,
      options,
    );
  }
}
