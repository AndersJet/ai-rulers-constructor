"""Capture explicit portable exports from a module's actual working tree."""
from __future__ import annotations

import re
from pathlib import Path

from .module_contracts import EXPORT_SCHEMA_VERSION, EXPORT_MANIFEST_SCHEMA_VERSION, require_protocol, checked_path, read_json, identity, file_identity, content_hash
from .module_git import repository_version, committed_file_identity
from .paths import resolve_layout
from .reconcile import parse_profile, select_profile_sections
from .rule_loading import validate_links, validate_index_routes
from .validation import validate_rule_metadata_text, TEMPLATE_RESIDUE_PATTERNS


def capture_export(*, project_root: Path, rulers_dir="documents/rulers", manifest="MODULE_EXPORT.json", code_root: Path | None = None) -> dict:
    layout = resolve_layout(project_root, rulers_dir)
    code_root = (code_root or layout.project_root).resolve()
    version = repository_version(code_root)
    manifest_path = checked_path(layout.rulers_root, manifest, required=True)
    manifest_hash = file_identity(manifest_path)
    definition = read_json(manifest_path)
    require_protocol(definition, "version", EXPORT_MANIFEST_SCHEMA_VERSION)
    if not isinstance(definition.get("rules"), list) or not definition["rules"]:
        raise ValueError("Export manifest requires version 1 and explicit rules")
    inputs = {manifest_path: manifest_hash}
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_json(state_path)
    inputs[state_path] = file_identity(state_path)
    rules = {}
    domains: dict[str, list[str]] = {}
    for item in definition["rules"]:
        if not isinstance(item, dict) or not isinstance(item.get("domain"), str) or not re.fullmatch(r"[A-Za-z0-9_-]+", item["domain"]):
            raise ValueError("Export rules require a domain identity")
        relative = item.get("path", "")
        if relative in rules or not relative.endswith(".md") or relative.startswith("scripts/") or relative in {"AGENTS.md", "PROJECT_PROFILE.md"}:
            raise ValueError("Export only explicitly named rule Markdown, without framework entry or State")
        source = checked_path(layout.rulers_root, relative, required=True)
        content = source.read_bytes()
        text = content.decode("utf-8")
        if validate_rule_metadata_text(text, relative) or any(pattern.search(text) for _, pattern, _ in TEMPLATE_RESIDUE_PATTERNS):
            raise ValueError(f"Invalid portable rule: {relative}")
        inputs[source] = content_hash(content)
        rules[relative] = {"domain": item["domain"], "text": text}
        domains.setdefault(item["domain"], []).append(relative)
    core = layout.rulers_root / "core"
    core_files = sorted(core.glob("*.md"))
    decisions = definition.get("core_decisions", {})
    if not isinstance(decisions, dict):
        raise ValueError("core_decisions must be an object")
    for path in core_files:
        relative = path.relative_to(layout.rulers_root).as_posix()
        checked_path(layout.rulers_root, relative, required=True)
        digest = file_identity(path)
        inputs[path] = digest
        metadata = state.get("managed_files", {}).get(f"{layout.rulers_dir}/{relative}", {})
        factory = metadata.get("source_sha256") == digest and not metadata.get("project_owned")
        if relative in rules:
            if factory:
                raise ValueError(f"Do not export unchanged framework core: {relative}")
            continue
        if not factory:
            decision = decisions.get(relative, {})
            if not isinstance(decision, dict) or not decision.get("reason"):
                raise ValueError(f"Classify customized core before export: {relative}")
            if decision.get("classification") == "module":
                projections = decision.get("rules", [])
                if not projections or any(name not in rules for name in projections):
                    raise ValueError(f"Module constraints need explicit exported rules: {relative}")
            elif decision.get("classification") != "framework-only":
                raise ValueError(f"Unknown core classification: {relative}")
    issues = validate_links(layout, paths=[f"{layout.rulers_dir}/{path}" for path in rules])
    for domain, names in domains.items():
        indexes = [name for name in names if Path(name).name == "INDEX.md"]
        if not indexes:
            raise ValueError(f"Export domain needs INDEX navigation: {domain}")
        top = min(indexes, key=lambda name: len(Path(name).parts))
        issues.extend(validate_index_routes(layout, index_path=f"{layout.rulers_dir}/{top}",
                                           paths=[f"{layout.rulers_dir}/{name}" for name in names]))
    if issues:
        raise ValueError("Export references are invalid: " + "; ".join(i.message for i in issues))
    scopes = definition.get("profile_scopes", [])
    if not isinstance(scopes, list) or not scopes or any(scope not in {"core", *domains} for scope in scopes):
        raise ValueError("Explicit profile_scopes must refer to exported domains or core")
    profile_path = checked_path(layout.rulers_root, "PROJECT_PROFILE.md", required=True)
    profile_text = profile_path.read_text(encoding="utf-8")
    parse_profile(profile_text, allowed_scopes=set(state.get("domains", {})) | set(domains) | {"core"})
    inputs[profile_path] = content_hash(profile_text.encode("utf-8"))
    profile = select_profile_sections(profile_text, scopes=set(scopes), always_sections=["项目身份"])
    commands = definition.get("commands", [])
    if not isinstance(commands, list):
        raise ValueError("Export commands must be an explicit list")
    for command in commands:
        if not isinstance(command, dict) or not isinstance(command.get("argv"), list) or not command["argv"] or not all(isinstance(x,str) and x for x in command["argv"]):
            raise ValueError("Commands declare argv; they are never executed during export")
        cwd = command.get("cwd", ".")
        if cwd != ".":
            checked_path(code_root, cwd)
    evidence = {}
    evidence_names = definition.get("evidence", [])
    if not isinstance(evidence_names, list):
        raise ValueError("Evidence must name explicit module-relative files")
    for relative in evidence_names:
        path = checked_path(code_root, relative, required=True)
        if code_root / layout.rulers_dir == path or code_root / layout.rulers_dir in path.parents:
            raise ValueError("Code evidence must be outside rule sources")
        evidence[relative] = file_identity(path)
        inputs[path] = evidence[relative]
    if sorted(core.glob("*.md")) != core_files or any(file_identity(path) != digest for path,digest in inputs.items()):
        raise ValueError("Source changed while capturing export; retry")
    if repository_version(code_root)["head"] != version["head"]:
        raise ValueError("Git version changed while capturing export; retry")
    input_hashes = {(path.relative_to(layout.project_root).as_posix() if path.is_relative_to(layout.project_root)
                     else path.relative_to(code_root).as_posix()): digest for path,digest in inputs.items()}
    version["dirty"] = version["dirty"] or any(committed_file_identity(code_root,relative) != digest for relative,digest in input_hashes.items())
    content = {"rules": rules, "profile": profile, "commands": commands, "evidence": evidence,
               "core_decisions": decisions, "profile_scopes": scopes}
    snapshot = {"export_version": EXPORT_SCHEMA_VERSION, **content, "content_id": identity(content),
                "source": {**version, "rulers_dir": layout.rulers_dir, "manifest": manifest,
                           "manifest_hash": manifest_hash,
                           "input_hashes": input_hashes}}
    snapshot["capture_id"] = identity(snapshot)
    return snapshot


def read_export_snapshot(path: Path) -> dict:
    snapshot = read_json(path)
    require_protocol(snapshot, "export_version", EXPORT_SCHEMA_VERSION)
    return snapshot
