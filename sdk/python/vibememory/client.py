"""Dependency-free Vibe Memory client. It performs no LLM calls."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request


def decision_profile_metadata(profile, metadata=None):
    """Build agent-supplied Decision metadata without asserting truth or authority."""

    profile = {**profile, "type": "decision", "version": 1}
    return {
        **(metadata or {}),
        "vibe_memory_profile": profile,
        "vibe_memory_profile_type": "decision",
        "vibe_memory_profile_version": 1,
        "vibe_memory_profile_state": profile["state"],
    }


def checkpoint_profile_metadata(profile, metadata=None):
    """Build data-only Checkpoint metadata; commands are not executed by the service."""

    profile = {**profile, "type": "checkpoint", "version": 1}
    return {
        **(metadata or {}),
        "vibe_memory_profile": profile,
        "vibe_memory_profile_type": "checkpoint",
        "vibe_memory_profile_version": 1,
        "vibe_memory_profile_state": profile["claimed_stage"],
        "vibe_memory_profile_observation": profile["observation_kind"],
    }


def failure_reproduction_profile_metadata(profile, metadata=None):
    """Build sanitized failure evidence; external references are never opened here."""

    profile = {**profile, "type": "failure_reproduction", "version": 1}
    external_statuses = {
        reference.get("verification", {}).get("status", "unverified")
        for reference in profile.get("evidence_references", [])
        if reference.get("kind") == "external"
    }
    reference_status = (
        "none"
        if not external_statuses
        else next(iter(external_statuses))
        if len(external_statuses) == 1
        else "mixed"
    )
    return {
        **(metadata or {}),
        "vibe_memory_failure_reproduction": profile,
        "vibe_memory_failure_profile_version": 1,
        "vibe_memory_failure_outcome": profile["outcome"],
        "vibe_memory_failure_stage": profile["failure"]["stage"],
        "vibe_memory_failure_reference_status": reference_status,
    }


def evidence_impact_review_profile_metadata(profile, metadata=None):
    """Build one review observation without collapsing conflicting reviewer claims."""

    profile = {**profile, "type": "evidence_impact_review", "version": 1}
    return {
        **(metadata or {}),
        "vibe_memory_evidence_impact_review": profile,
        "vibe_memory_evidence_impact_profile_version": 1,
        "vibe_memory_evidence_impact": profile["impact"],
        "vibe_memory_evidence_impact_target_kind": profile["target"]["kind"],
    }


def agent_state_profile_metadata(profile, metadata=None):
    """Build harness-neutral task state; record version remains the OCC coordinate."""

    profile = {**profile, "type": "agent_state", "version": 1}
    return {
        **(metadata or {}),
        "vibe_memory_agent_state": profile,
        "vibe_memory_agent_state_profile_version": 1,
        "vibe_memory_agent_state_project_id": profile["project_id"],
        "vibe_memory_agent_state_task_id": profile["task_id"],
        "vibe_memory_agent_state_status": profile["status"],
        "vibe_memory_agent_state_version": profile["state_version"],
        "vibe_memory_agent_state_harness": profile["reported_harness"]["id"],
    }


def skill_execution_profile_metadata(profile, metadata=None):
    """Build an external harness execution report; this helper executes nothing."""

    profile = {**profile, "type": "skill_execution", "version": 1}
    return {
        **(metadata or {}),
        "vibe_memory_skill_execution": profile,
        "vibe_memory_skill_execution_profile_version": 1,
        "vibe_memory_skill_id": profile["skill"]["id"],
        "vibe_memory_skill_execution_status": profile["reported_status"],
        "vibe_memory_skill_verification_status": profile["verification_status"],
        "vibe_memory_skill_execution_harness": profile["reported_harness"]["id"],
    }


class VibeMemoryError(RuntimeError):
    def __init__(self, status, body, *, headers=None):
        try:
            payload = json.loads(body)
        except (TypeError, json.JSONDecodeError):
            payload = {}
        error = payload.get("error") if isinstance(payload, dict) else {}
        error = error if isinstance(error, dict) else {}
        super().__init__(f"Vibe Memory {status}: {error.get('reason_code') or body}")
        self.status = status
        self.body = body
        self.payload = payload
        self.code = error.get("reason_code")
        self.retryable = bool(error.get("retryable"))
        self.request_id = error.get("request_id") or (headers or {}).get("X-Request-ID")


class VibeMemoryCancelled(RuntimeError):
    """Raised between HTTP operations when the caller's cancellation hook is set."""


class VibeMemoryClient:
    def __init__(
        self,
        base_url,
        token,
        namespace="default",
        timeout=20,
        contract_version="1.1",
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.namespace = namespace
        self.timeout = timeout
        self.contract_version = contract_version

    @staticmethod
    def _check_cancelled(cancelled):
        if cancelled is not None and cancelled():
            raise VibeMemoryCancelled("Vibe Memory request cancelled")

    def _request(self, path, method="GET", payload=None, retry=False, *, cancelled=None):
        self._check_cancelled(cancelled)
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "X-Vibe-Memory-Namespace": self.namespace,
                "Vibe-Memory-Contract-Version": self.contract_version,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return None if response.status == 204 else json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and retry:
                delay = min(int(error.headers.get("Retry-After", "1")), 30)
                deadline = time.monotonic() + max(delay, 0)
                while time.monotonic() < deadline:
                    self._check_cancelled(cancelled)
                    time.sleep(min(0.1, deadline - time.monotonic()))
                return self._request(path, method, payload, False, cancelled=cancelled)
            raise VibeMemoryError(
                error.code,
                error.read().decode(errors="replace"),
                headers=error.headers,
            ) from None

    def get(self, record_id, *, cancelled=None):
        return self._request(
            "/v1/records/" + urllib.parse.quote(record_id, safe=""), cancelled=cancelled
        )

    def search(
        self,
        keywords,
        match_mode="hybrid",
        *,
        projection="minimal",
        byte_limit=16384,
        limit=8,
        cancelled=None,
    ):
        return self._request(
            "/v1/search",
            "POST",
            {
                "keywords": keywords,
                "match_mode": match_mode,
                "projection": projection,
                "byte_limit": byte_limit,
                "limit": limit,
            },
            True,
            cancelled=cancelled,
        )

    def create(self, content, keywords, client_request_id=None, *, cancelled=None):
        payload = {"content": content, "keywords": keywords, "kind": "fact"}
        if client_request_id:
            payload["client_request_id"] = client_request_id
        return self._request(
            "/v1/memories",
            "POST",
            payload,
            bool(client_request_id),
            cancelled=cancelled,
        )

    def create_with_metadata(
        self, content, keywords, metadata, client_request_id=None, *, cancelled=None
    ):
        payload = {
            "content": content,
            "keywords": keywords,
            "kind": "fact",
            "metadata": metadata,
        }
        if client_request_id:
            payload["client_request_id"] = client_request_id
        return self._request(
            "/v1/memories",
            "POST",
            payload,
            bool(client_request_id),
            cancelled=cancelled,
        )

    def correct(
        self,
        previous_id,
        expected_previous_version,
        replacement,
        reason,
        client_request_id,
        *,
        cancelled=None,
    ):
        return self._request(
            "/v1/corrections/memories",
            "POST",
            {
                "previous_id": previous_id,
                "expected_previous_version": expected_previous_version,
                "replacement": {**replacement, "kind": replacement.get("kind", "fact")},
                "relation": "CORRECTS",
                "correction_scope": "full",
                "reason": reason,
                "client_request_id": client_request_id,
            },
            True,
            cancelled=cancelled,
        )

    def list(self, limit=50, offset=0, *, cancelled=None):
        return self._request(
            f"/v1/records?limit={limit}&offset={offset}", cancelled=cancelled
        )

    def iter_records(self, limit=50, offset=0, *, cancelled=None):
        """Yield deterministic API pages; cancellation is checked between requests."""

        while True:
            page = self.list(limit, offset, cancelled=cancelled)
            yield page
            items = page.get("items", [])
            if len(items) < limit:
                return
            offset += len(items)

    def create_entities(self, items, *, cancelled=None):
        return self._request(
            "/v1/entities/batch",
            "POST",
            {"items": items, "return": "minimal", "atomic": False},
            cancelled=cancelled,
        )

    def context_bundle(self, *, cancelled=None, **selectors):
        selectors.setdefault("projection", "minimal")
        selectors.setdefault("byte_limit", 32768)
        return self._request(
            "/v1/context-bundle", "POST", selectors, True, cancelled=cancelled
        )

    def evidence_impact_candidates(
        self,
        evidence_record_id,
        evidence_version,
        candidate_limit=100,
        *,
        cancelled=None,
    ):
        return self._request(
            "/v1/evidence-impact/candidates",
            "POST",
            {
                "evidence_record_id": evidence_record_id,
                "evidence_version": evidence_version,
                "candidate_limit": candidate_limit,
            },
            False,
            cancelled=cancelled,
        )
