"""Deterministic current-connection authorization and capability contracts."""

from __future__ import annotations

from .clock import utc_now_iso

CONTRACT_VERSION = "1.1"


# The registry describes server features independently from the grant carried by
# one credential.  It intentionally does not inspect records or enumerate other
# users/connections.
CAPABILITY_RULES = (
    ("memory", "read", "memory:read", "memory:read", True),
    ("memory", "search", "memory:read", "memory:read", True),
    ("memory", "create", "memory:write", "memory:write", True),
    ("memory", "update", "memory:write", "memory:write", True),
    ("memory", "archive", "memory:write", "memory:write", True),
    ("memory", "restore", "memory:write", "memory:write", True),
    ("memory", "delete", "memory:write", None, True),
    ("document", "read", "memory:read", "memory:read", True),
    ("document", "create", "memory:write", "memory:write", True),
    ("document", "update", "memory:write", "memory:write", True),
    ("document", "archive", "memory:write", "memory:write", True),
    ("entity", "read", "memory:read", "memory:read", True),
    ("entity", "create", "memory:write", "memory:write", True),
    ("entity", "update", "memory:write", "memory:write", True),
    ("entity", "archive", "memory:write", "memory:write", True),
    ("relation", "read", "memory:read", "memory:read", True),
    ("relation", "create", "memory:write", "memory:write", True),
    ("relation", "update", "memory:write", "memory:write", True),
    ("graph", "read", "memory:read", "memory:read", True),
    ("graph", "audit", "memory:read", "memory:read", True),
    ("graph", "diff", "memory:read", "memory:read", True),
    ("graph", "apply", "memory:write", "memory:write", True),
    ("file", "read", "files:read", None, True),
    ("file", "upload", "files:write", None, True),
    ("file", "delete", "files:write", None, True),
    ("message", "read", "messages:read", "memory:read", True),
    ("message", "send", "messages:write", "memory:write", True),
    ("message", "acknowledge", "messages:write", "memory:write", True),
    ("event", "poll", "events:read", "memory:read", True),
    ("event", "stream", "events:read", None, True),
    ("feature_request", "read", "feature:write", "memory:read", True),
    ("feature_request", "submit", "feature:write", "feature:write", True),
    ("vault", "list", "vault:read", "vault:read", True),
    ("vault", "read", "vault:read", "vault:read", True),
    ("admin", "feature_requests", "feature_request_operator", None, True),
    ("admin", "users", "admin", None, True),
    ("portable_archive", "export", "memory:read", None, True),
    ("portable_archive", "import", "memory:write", None, True),
    ("namespace", "select", "memory:read", "memory:read", True),
    ("temporal", "valid_time", "memory:read", "memory:read", True),
    ("temporal", "historical_recorded_time", None, None, False),
)


def build_auth_context(
    *,
    connection_id: str,
    connection_name: str,
    transport: str,
    credential_type: str,
    audience: str,
    principal_id: str,
    principal_name: str,
    grants,
    vault_access: bool = False,
    vault_names=None,
    feature_request_operator: bool = False,
    is_admin: bool = False,
    expires_at=None,
    namespace_id="default",
    namespace_grants=None,
):
    """Return only facts proven by the credential used for this request."""

    grant_list = sorted(set(grants or []))
    names = sorted(set(vault_names or []))
    return {
        "schema_version": CONTRACT_VERSION,
        "context_ref": f"connection:{connection_id}",
        "checked_at": utc_now_iso(),
        "connection": {
            "id": connection_id,
            "name": connection_name,
            "transport": transport,
            "credential_type": credential_type,
            "audience": audience,
            "validity": "valid",
            "expires_at": expires_at,
        },
        "principal": {
            "ref": f"account:{principal_id}",
            "name": principal_name,
            "scope": "current_account",
        },
        "authorization": {
            "grants": grant_list,
            "grant_source": "current_credential",
            "other_connections_checked": False,
            "permission_inheritance": False,
            "vault_scope_allowed": vault_access or "vault:read" in grant_list,
            "vault_resource_policy": (
                "explicit_per_entry" if transport == "mcp" else "connection_wide"
            ),
            "vault_granted_entry_count": len(names) if transport == "mcp" else None,
            "feature_request_operator": bool(feature_request_operator),
            "admin": bool(is_admin),
        },
        "project_scope": {
            "status": "enforced",
            "namespace_id": namespace_id,
            "selection": "X-Vibe-Memory-Namespace",
            "enforcement": "isolated_owner_partition",
            "grants": namespace_grants,
        },
        "external_service_permissions": {
            "status": "not_evaluated",
            "reason": "Vibe Memory cannot inspect host or third-party service policy.",
        },
    }


def _authorization_result(auth_context, resource, operation, rest_grant, mcp_grant, supported):
    if not supported:
        return {
            "status": "denied",
            "reason_code": "UNSUPPORTED_CAPABILITY",
            "required_grant": None,
        }

    transport = auth_context["connection"]["transport"]
    grants = set(auth_context["authorization"]["grants"])
    required = mcp_grant if transport == "mcp" else rest_grant
    if required is None:
        return {
            "status": "denied",
            "reason_code": "TOOL_NOT_EXPOSED" if transport == "mcp" else "UNSUPPORTED_TRANSPORT",
            "required_grant": None,
        }
    if required == "admin":
        allowed = auth_context["authorization"]["admin"]
    elif required == "feature_request_operator":
        allowed = auth_context["authorization"]["feature_request_operator"]
    elif required == "vault:read" and transport != "mcp":
        allowed = auth_context["authorization"]["vault_scope_allowed"]
    else:
        allowed = required in grants
    if not allowed:
        return {
            "status": "denied",
            "reason_code": "PERMISSION_REQUIRED",
            "required_grant": required,
        }
    if resource == "vault" and operation == "read" and transport == "mcp":
        return {
            "status": "conditional",
            "reason_code": "RESOURCE_GRANT_REQUIRED",
            "required_grant": "vault:read",
        }
    return {"status": "allowed", "reason_code": "ALLOWED", "required_grant": required}


def capability_contract(auth_context):
    capabilities = []
    for resource, operation, rest_grant, mcp_grant, supported in CAPABILITY_RULES:
        result = _authorization_result(
            auth_context, resource, operation, rest_grant, mcp_grant, supported
        )
        capabilities.append(
            {
                "resource": resource,
                "operation": operation,
                "feature_status": "supported" if supported else "unsupported",
                "authorization": result,
            }
        )
    return {
        "schema_version": CONTRACT_VERSION,
        "context_ref": auth_context["context_ref"],
        "checked_at": utc_now_iso(),
        "evaluation": "metadata_only",
        "capabilities": capabilities,
    }


def permission_check(auth_context, resource, operation):
    for item in capability_contract(auth_context)["capabilities"]:
        if item["resource"] == resource and item["operation"] == operation:
            return {
                "schema_version": CONTRACT_VERSION,
                "context_ref": auth_context["context_ref"],
                "checked_at": utc_now_iso(),
                "evaluation": "metadata_only",
                "resource": resource,
                "operation": operation,
                "feature_status": item["feature_status"],
                "authorization": item["authorization"],
                "request_will_reauthorize": True,
                "resource_existence_checked": False,
            }
    return {
        "schema_version": CONTRACT_VERSION,
        "context_ref": auth_context["context_ref"],
        "checked_at": utc_now_iso(),
        "evaluation": "metadata_only",
        "resource": resource,
        "operation": operation,
        "feature_status": "unknown",
        "authorization": {
            "status": "unknown",
            "reason_code": "UNKNOWN_CAPABILITY",
            "required_grant": None,
        },
        "request_will_reauthorize": True,
        "resource_existence_checked": False,
    }


def structured_error(
    *,
    request_id,
    context_ref,
    operation,
    resource_type,
    reason_code,
    retryable=False,
    required_action=None,
):
    return {
        "schema_version": CONTRACT_VERSION,
        "context": {"ref": context_ref} if context_ref else None,
        "operation": operation,
        "resource_type": resource_type,
        "reason_code": reason_code,
        "retryable": bool(retryable),
        "required_action": required_action,
        "request_id": request_id,
    }
