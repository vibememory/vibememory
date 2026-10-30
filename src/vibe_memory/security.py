"""Deterministic record provenance and quarantine policy.

This module deliberately performs no model inference and calls no external service.
Connected agents may attach their own scan verdict and evidence; the service keeps
that provenance visible and applies conservative retrieval defaults.
"""

import re
import unicodedata
from hashlib import sha256

from .clock import utc_now_iso


class SecurityPolicyError(ValueError):
    pass


HIGH_RISK_WARNINGS = {
    "control_characters",
    "unicode_format_controls",
    "instruction_override_pattern",
    "external_transmission_pattern",
    "hidden_markup",
    "scanner_reported_suspicious",
    "scanner_reported_malicious",
}

_INSTRUCTION_OVERRIDE = re.compile(
    r"(?:ignore|disregard|override|forget)\s+(?:all\s+|any\s+|the\s+)?"
    r"(?:(?:previous|prior)\s+)?(?:(?:system|developer|user)\s+)?"
    r"(?:instructions?|messages?|prompts?|scope|rules?|polic(?:y|ies))",
    re.IGNORECASE,
)
_HIDDEN_MARKUP = re.compile(
    r"<!--|display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\D|$)",
    re.IGNORECASE,
)
_EXTERNAL_TRANSMISSION = re.compile(
    r"(?:post|send|upload|exfiltrat(?:e|ion)|transmit)\b.{0,120}"
    r"(?:https?://|webhook|remote|external|environment|credentials?|secrets?|tokens?)",
    re.IGNORECASE | re.DOTALL,
)


def record_fingerprint(title: str, content: str) -> str:
    return sha256((title + "\0" + content).encode("utf-8")).hexdigest()


def _provenance_dict(value) -> dict:
    if hasattr(value, "model_dump"):
        result = value.model_dump(mode="json")
    else:
        result = dict(value or {})
    defaults = {
        "source_type": "agent-authored",
        "origin_agent": "",
        "origin_url": "",
        "collected_at": None,
        "content_type": "",
        "scan_verdict": "not_scanned",
        "scan_evidence": [],
    }
    defaults.update(result)
    defaults["scan_evidence"] = list(defaults.get("scan_evidence") or [])
    return defaults


def deterministic_warnings(title: str, content: str, provenance: dict) -> list[str]:
    text = title + "\n" + content
    warnings = []
    if unicodedata.normalize("NFKC", text) != text:
        warnings.append("nfkc_normalization_changed")
    if any(
        (ord(character) < 32 and character not in "\t\n\r") or ord(character) == 127
        for character in text
    ):
        warnings.append("control_characters")
    if any(unicodedata.category(character) == "Cf" for character in text):
        warnings.append("unicode_format_controls")
    if _INSTRUCTION_OVERRIDE.search(text):
        warnings.append("instruction_override_pattern")
    if _EXTERNAL_TRANSMISSION.search(text):
        warnings.append("external_transmission_pattern")
    if _HIDDEN_MARKUP.search(text):
        warnings.append("hidden_markup")
    if provenance["source_type"] in {"external", "imported"} and not (
        provenance.get("origin_agent") or provenance.get("origin_url")
    ):
        warnings.append("missing_external_origin")
    verdict = provenance.get("scan_verdict", "not_scanned")
    if verdict == "suspicious":
        warnings.append("scanner_reported_suspicious")
    elif verdict == "malicious":
        warnings.append("scanner_reported_malicious")
    return warnings


def prepare_record_security(title: str, content: str, provenance) -> dict:
    provenance = _provenance_dict(provenance)
    warnings = deterministic_warnings(title, content, provenance)
    external = provenance["source_type"] in {"external", "imported"}
    high_risk = bool(HIGH_RISK_WARNINGS.intersection(warnings))
    trust_level = (
        "untrusted" if external or provenance["scan_verdict"] == "malicious" else "trusted"
    )
    state = "quarantined" if external or high_risk else "active"
    created = utc_now_iso()
    return {
        "trust_level": trust_level,
        "security_state": state,
        "provenance": provenance,
        "content_hash": record_fingerprint(title, content),
        "security_warnings": warnings,
        "security_history": [
            {
                "at": created,
                "version": 1,
                "state": state,
                "trust_level": trust_level,
                "scan_verdict": provenance["scan_verdict"],
                "reason": "record created",
            }
        ],
    }


def reassess_record_security(record: dict, title: str, content: str, version: int) -> dict:
    provenance = _provenance_dict(record.get("provenance"))
    content_hash = record_fingerprint(title, content)
    content_changed = content_hash != record.get("content_hash")
    scan_invalidated = content_changed and (
        provenance["scan_verdict"] != "not_scanned" or provenance["scan_evidence"]
    )
    if scan_invalidated:
        provenance["scan_verdict"] = "not_scanned"
        provenance["scan_evidence"] = []
    warnings = deterministic_warnings(title, content, provenance)
    external = provenance["source_type"] in {"external", "imported"}
    trust_level = (
        "untrusted" if content_changed and external else record.get("trust_level", "trusted")
    )
    previous_state = record.get("security_state", "active")
    state = previous_state
    if trust_level == "untrusted" or HIGH_RISK_WARNINGS.intersection(warnings):
        state = "quarantined"
    history = list(record.get("security_history") or [])
    if state != previous_state or warnings != list(record.get("security_warnings") or []):
        history.append(
            {
                "at": utc_now_iso(),
                "version": version,
                "state": state,
                "trust_level": trust_level,
                "scan_verdict": provenance["scan_verdict"],
                "reason": (
                    "external content changed; trust and prior scan evidence invalidated"
                    if scan_invalidated
                    else "record content reassessed by deterministic security policy"
                ),
            }
        )
    return {
        "trust_level": trust_level,
        "security_state": state,
        "provenance": provenance,
        "content_hash": content_hash,
        "security_warnings": warnings,
        "security_history": history,
    }


def apply_security_update(record: dict, data) -> dict:
    provenance = _provenance_dict(record.get("provenance"))
    if data.scan_verdict is not None:
        provenance["scan_verdict"] = data.scan_verdict
    if data.scan_evidence is not None:
        provenance["scan_evidence"] = list(data.scan_evidence)
    warnings = deterministic_warnings(record["title"], record["content"], provenance)
    trust_level = data.trust_level or record.get("trust_level", "trusted")
    state = data.state or record.get("security_state", "active")
    if state == "active":
        if trust_level != "trusted":
            raise SecurityPolicyError("active records must be explicitly trusted")
        if provenance["scan_verdict"] in {"suspicious", "malicious"}:
            raise SecurityPolicyError("suspicious or malicious records must remain quarantined")
        if HIGH_RISK_WARNINGS.intersection(warnings) and provenance["scan_verdict"] != "safe":
            raise SecurityPolicyError(
                "records with high-risk deterministic warnings require a safe scan verdict"
            )
    history = list(record.get("security_history") or [])
    history.append(
        {
            "at": utc_now_iso(),
            "version": record["version"] + 1,
            "state": state,
            "trust_level": trust_level,
            "scan_verdict": provenance["scan_verdict"],
            "reason": data.reason,
        }
    )
    return {
        "trust_level": trust_level,
        "security_state": state,
        "provenance": provenance,
        "content_hash": record_fingerprint(record["title"], record["content"]),
        "security_warnings": warnings,
        "security_history": history,
    }


def record_is_retrievable(
    record: dict, *, include_untrusted: bool = False, include_quarantined: bool = False
) -> bool:
    if record.get("trust_level", "trusted") != "trusted" and not include_untrusted:
        return False
    if record.get("security_state", "active") != "active" and not include_quarantined:
        return False
    return True
