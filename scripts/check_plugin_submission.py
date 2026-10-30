#!/usr/bin/env python3
"""Validate and, only when fully ready, package the public ChatGPT plugin upload."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLUGIN = ROOT / "plugins" / "vibe-memory"
CATEGORIES = {
    "Business & Operations",
    "Communication",
    "Creativity",
    "Data & Analytics",
    "Developer Tools",
    "Education & Research",
    "Entertainment",
    "Finance",
    "Healthcare",
    "Other",
    "Productivity",
    "Scientific Research",
    "Security",
    "Travel",
}
URL_PURPOSE = {
    "websiteURL": ("vibe memory", "memory"),
    "supportURL": ("vibe memory", "support", "지원"),
    "privacyPolicyURL": ("vibe memory", "privacy", "개인정보"),
    "termsOfServiceURL": ("vibe memory", "terms", "이용약관"),
}
REQUIRED_BLOCKERS = {"reviewer_access", "portal_identity", "portal_countries"}
ALLOWED_PACKAGE_ROOTS = {"plugin.json", "mcp.json", "assets", "skills"}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return value


def semver(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?",
        value,
    ) is not None


def valid_https(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 1024:
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


def local_url_content(url: str, site_dir: Path) -> str:
    parsed = urlsplit(url)
    if parsed.netloc != "vibememory.io":
        raise RuntimeError(f"cannot map external URL to local export: {url}")
    relative = parsed.path.strip("/")
    candidates = [site_dir / "index.html"] if not relative else [
        site_dir / f"{relative}.html",
        site_dir / relative / "index.html",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").casefold()
    raise RuntimeError(f"local export has no page for {url}")


def remote_url_content(url: str) -> str:
    request = Request(url, headers={"User-Agent": "vibe-memory-submission-check/1"})
    try:
        with urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "text/plain"}:
                raise RuntimeError(f"unexpected content type {content_type}")
            body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise RuntimeError("response exceeds 2 MiB inspection limit")
            return body.decode("utf-8", "replace").casefold()
    except (HTTPError, URLError) as error:
        raise RuntimeError(str(error)) from error


def check_url_purpose(field: str, url: str, content: str) -> str | None:
    groups = URL_PURPOSE[field]
    if groups[0] not in content:
        return "page does not identify Vibe Memory"
    if field != "websiteURL" and not any(marker in content for marker in groups[1:]):
        return f"page does not contain a {field} purpose marker"
    return None


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError("not a PNG with an IHDR chunk")
    return struct.unpack(">II", data[16:24])


def package_files(plugin: Path) -> list[Path]:
    files = []
    for relative in (Path("plugin.json"), Path("mcp.json"), Path("assets/icon.png")):
        if (plugin / relative).is_file():
            files.append(relative)
    for path in sorted((plugin / "skills").rglob("*")):
        if path.is_file():
            files.append(path.relative_to(plugin))
    return files


def validate_archive(path: Path, expected: list[Path]) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise RuntimeError("archive contains an unsafe path")
        if set(names) != {str(item).replace("\\", "/") for item in expected}:
            raise RuntimeError("archive inventory does not match the approved package inventory")
        for info in archive.infolist():
            if info.is_dir() or info.external_attr >> 16 & 0o170000 == 0o120000:
                raise RuntimeError(f"archive contains a directory or symlink entry: {info.filename}")


def validate(plugin: Path, site_dir: Path | None, network: bool) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    manifest = load_json(plugin / "plugin.json")
    mcp = load_json(plugin / "mcp.json")
    readiness = load_json(plugin / "submission-readiness.json")

    def error(code: str, message: str) -> None:
        findings.append(Finding("ERROR", code, message))

    def blocked(code: str, message: str) -> None:
        findings.append(Finding("BLOCKED", code, message))

    if manifest.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        error("plugin_schema", "plugin.json has the wrong or missing schema")
    if manifest.get("name") != "vibe-memory":
        error("plugin_name", "plugin identity must remain vibe-memory")
    version = manifest.get("version")
    if not semver(version):
        error("version", "plugin version must be strict SemVer")
    if readiness.get("packageVersion") != version:
        error("version_sync", "submission-readiness packageVersion differs from plugin.json")
    try:
        project_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
        if project_version != version:
            error("version_sync", "pyproject.toml version differs from plugin.json")
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        error("version_sync", f"cannot inspect pyproject.toml: {exc}")

    openai = manifest.get("extensions", {}).get("com.openai", {})
    interface = openai.get("interface", {})
    for field, maximum in (
        ("displayName", 30),
        ("shortDescription", 30),
        ("longDescription", 4000),
        ("developerName", 80),
    ):
        value = interface.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            error(field, f"{field} must be nonblank and at most {maximum} characters")
    if interface.get("category") not in CATEGORIES:
        error("category", "category is not an exact supported title")
    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
        error("defaultPrompt", "defaultPrompt must contain one to three prompts")
    elif any(
        not isinstance(prompt, str)
        or not prompt.strip()
        or "\n" in prompt
        or len(prompt) > 128
        for prompt in prompts
    ) or len({" ".join(prompt.split()) for prompt in prompts}) != len(prompts):
        error("defaultPrompt", "default prompts must be unique nonblank single lines <=128 chars")

    known = {
        item.get("id"): item.get("reason")
        for item in readiness.get("knownBlockers", [])
        if isinstance(item, dict)
    }
    if None in known or any(not isinstance(reason, str) or not reason.strip() for reason in known.values()):
        error("blocker_schema", "known blockers need unique nonblank id and reason values")

    for field in URL_PURPOSE:
        value = interface.get(field)
        if value is None and field in {"privacyPolicyURL", "termsOfServiceURL"}:
            if field in known:
                blocked(field, known[field])
            else:
                error(field, f"{field} is required for public submission")
            continue
        if not valid_https(value):
            error(field, f"{field} must be an absolute public HTTPS URL")
            continue
        try:
            if site_dir is not None and urlsplit(value).netloc == "vibememory.io":
                content = local_url_content(value, site_dir)
            elif network:
                content = remote_url_content(value)
            else:
                raise RuntimeError("purpose check needs --site-dir or --network")
            purpose_error = check_url_purpose(field, value, content)
            if purpose_error:
                error(field, purpose_error)
        except RuntimeError as exc:
            error(field, f"cannot verify URL content purpose: {exc}")

    for icon_field in ("logo", "composerIcon"):
        value = interface.get(icon_field)
        if not isinstance(value, str) or not value.startswith("./"):
            error(icon_field, f"{icon_field} must be a contained relative path")
            continue
        path = (plugin / value).resolve()
        if plugin.resolve() not in path.parents or not path.is_file():
            error(icon_field, f"{icon_field} does not resolve to a packaged file")
            continue
        if path.suffix.casefold() != ".png" or path.stat().st_size > 5 * 1024 * 1024:
            error(icon_field, f"{icon_field} must reference a PNG no larger than 5 MiB")
            continue
        try:
            width, height = png_dimensions(path)
            minimum = 256 if icon_field == "logo" else 48
            if width != height or width < minimum:
                error(icon_field, f"{icon_field} must be square and at least {minimum}x{minimum}")
        except (OSError, RuntimeError) as exc:
            error(icon_field, str(exc))

    if (plugin / ".app.json").exists() or manifest.get("apps") is not None or openai.get("apps") is not None:
        error("app_binding", "public upload source must not contain .app.json or apps declarations")
    for path in plugin.rglob("*.json"):
        if path.name == ".app.json":
            error("app_binding", f"public upload source contains {path.relative_to(plugin)}")

    servers = mcp.get("mcpServers")
    if not isinstance(servers, dict) or set(servers) != {"vibe-memory"}:
        error("mcp", "mcp.json must declare exactly the verified vibe-memory server")
    else:
        server = servers["vibe-memory"]
        if server.get("type") != "streamable-http" or server.get("url") != "https://vibememory.io/mcp":
            error("mcp", "MCP transport or endpoint differs from the verified public endpoint")

    review = openai.get("review", {})
    review_prompts = review.get("prompts")
    if not isinstance(review_prompts, list) or not 1 <= len(review_prompts) <= 20:
        error("review_prompts", "review prompts must contain 1-20 items")
    elif any(not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000 for prompt in review_prompts):
        error("review_prompts", "review prompts must be nonblank strings <=4000 characters")
    cases = review.get("test_cases", {})
    positive = cases.get("positive") if isinstance(cases, dict) else None
    negative = cases.get("negative") if isinstance(cases, dict) else None
    if not isinstance(positive, list) or len(positive) != 5:
        error("review_cases", "exactly five positive review cases are required")
    else:
        for index, case in enumerate(positive, 1):
            if not isinstance(case, dict) or not all(
                isinstance(case.get(field), str) and case[field].strip()
                for field in ("description", "prompt", "tools_triggered", "expected_behavior")
            ):
                error("review_cases", f"positive case {index} has missing or non-string fields")
    if not isinstance(negative, list) or len(negative) != 3:
        error("review_cases", "exactly three negative review cases are required")
    else:
        for index, case in enumerate(negative, 1):
            if not isinstance(case, dict) or not all(
                isinstance(case.get(field), str) and case[field].strip()
                for field in ("description", "prompt", "expected_behavior")
            ):
                error("review_cases", f"negative case {index} has missing or non-string fields")

    demo = review.get("demo_recording_url")
    if not demo:
        if "demo_recording_url" in known:
            blocked("demo_recording_url", known["demo_recording_url"])
        else:
            error("demo_recording_url", "a verified public demo recording URL is required")
    elif not valid_https(demo):
        error("demo_recording_url", "demo recording URL must be an absolute public HTTPS URL")
    publication = openai.get("publication", {})
    if publication.get("countries") != []:
        error("countries", "all-supported-country targeting is represented by an explicit empty list")
    if readiness.get("commerce") != {
        "payments": False,
        "purchases": False,
        "portalVerified": False,
    }:
        error("commerce", "readiness must truthfully declare no payments or purchases pending portal verification")

    for code in REQUIRED_BLOCKERS:
        if code in known:
            blocked(code, known[code])
        else:
            error(code, f"missing explicit readiness gate: {code}")

    sys.path.insert(0, str(ROOT / "src"))
    try:
        from vibe_memory.mcp import TOOLS

        tool_names = {tool.get("name") for tool in TOOLS}
        for tool in TOOLS:
            annotations = tool.get("annotations", {})
            for field in ("readOnlyHint", "openWorldHint", "destructiveHint"):
                if type(annotations.get(field)) is not bool:
                    error("tool_annotations", f"{tool.get('name')} has a non-boolean {field}")
        if isinstance(positive, list):
            for index, case in enumerate(positive, 1):
                if not isinstance(case, dict) or not isinstance(case.get("tools_triggered"), str):
                    continue
                named_tools = {
                    name.strip() for name in case["tools_triggered"].split(",") if name.strip()
                }
                unknown = named_tools - tool_names
                if unknown:
                    error(
                        "review_cases",
                        f"positive case {index} names unknown MCP tools: {sorted(unknown)}",
                    )
    except Exception as exc:  # pragma: no cover - reported as a readiness failure
        error("tool_annotations", f"cannot inspect MCP tool annotations: {exc}")

    return findings, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", type=Path, default=DEFAULT_PLUGIN)
    parser.add_argument("--site-dir", type=Path, help="Inspect same-origin URL content in a static export")
    parser.add_argument("--network", action="store_true", help="Fetch and inspect public URL content")
    parser.add_argument(
        "--acknowledge-blockers",
        action="store_true",
        help="Exit successfully when only explicitly declared external blockers remain",
    )
    parser.add_argument("--archive", type=Path, help="Write a public upload ZIP only when strictly ready")
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    plugin = args.plugin.resolve()

    try:
        findings, manifest = validate(plugin, args.site_dir, args.network)
    except RuntimeError as exc:
        print(f"ERROR validation {exc}")
        return 2

    for finding in findings:
        print(f"{finding.level} {finding.code}: {finding.message}")
    errors = [finding for finding in findings if finding.level == "ERROR"]
    blockers = [finding for finding in findings if finding.level == "BLOCKED"]
    report = {
        "plugin": manifest.get("name"),
        "version": manifest.get("version"),
        "ready": not errors and not blockers,
        "errors": [finding.__dict__ for finding in errors],
        "blockers": [finding.__dict__ for finding in blockers],
    }
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if errors:
        print(f"FAIL {len(errors)} validation error(s), {len(blockers)} declared blocker(s)")
        return 1
    if blockers and not args.acknowledge_blockers:
        print(f"BLOCKED {len(blockers)} public-submission prerequisite(s) remain")
        return 1
    if args.archive:
        if blockers:
            print("FAIL an upload archive cannot be written while blockers remain")
            return 1
        if not args.network:
            print("FAIL --archive requires --network to verify the live purpose and access of every URL")
            return 1
        files = package_files(plugin)
        unexpected_roots = {path.parts[0] for path in files} - ALLOWED_PACKAGE_ROOTS
        if unexpected_roots:
            print(f"FAIL unexpected package roots: {sorted(unexpected_roots)}")
            return 1
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in files:
                archive.write(plugin / relative, str(relative).replace("\\", "/"))
        try:
            validate_archive(args.archive, files)
        except RuntimeError as exc:
            print(f"FAIL archive validation: {exc}")
            return 1
        print(f"PASS wrote verified upload archive {args.archive}")
    else:
        state = "declared blockers acknowledged" if blockers else "submission source ready"
        print(f"PASS {state}; package inventory, listing, review cases, and tool annotations validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
