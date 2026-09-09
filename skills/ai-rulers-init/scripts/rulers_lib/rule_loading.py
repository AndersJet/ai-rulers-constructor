"""Resolve explicit rule dependencies and validate rule links without model routing."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .issues import ValidationIssue
from .paths import resolve_safe_child
from .domains import rule_owner
from .reconcile import select_profile_sections


def resolve_reference(layout, source: Path, value: str) -> Path | None:
    value = value.strip().strip('"\'<>')
    if urlsplit(value).scheme or value.startswith("#"):
        return None
    value = unquote(value.split("#", 1)[0])
    if not value:
        return None
    root_relative = value.startswith(layout.rulers_dir + "/") or value in {"AGENTS.md", "CLAUDE.md"}
    candidate = Path(value) if root_relative else source.parent.relative_to(layout.project_root) / value
    # Relative sibling/parent links may stay within the project but never escape it.
    target = (layout.project_root / candidate).resolve()
    if not target.is_relative_to(layout.project_root) or Path(value).is_absolute():
        raise ValueError(f"Rule reference escapes project: {value}")
    return target


def references(text):
    from .validation import FENCED_YAML_RE, _metadata_list
    match = FENCED_YAML_RE.search(text)
    dependencies = _metadata_list(match.group(1), "must_load_with") or [] if match else []
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    return dependencies, links


def index_links(text):
    _, links = references(text)
    return links + re.findall(r"`([^`\n]+\.md(?:#[^`\n]*)?)`", text)


def validate_links(layout, *, paths):
    issues = []
    for relative in paths:
        source = resolve_safe_child(layout.project_root, relative)
        text = source.read_text(encoding="utf-8")
        dependencies, links = references(text)
        if source.name == "INDEX.md":
            links = index_links(text)
        for value in dependencies + links:
            try:
                target = resolve_reference(layout, source, value)
                if target is not None and not target.is_file():
                    raise ValueError(f"Missing rule reference: {relative} -> {value}")
            except ValueError as exc:
                issues.append(ValidationIssue("VR107", str(exc), relative))
    return issues


def validate_index_routes(layout, *, index_path: str, paths):
    """Every adopted file must be discoverable through domain INDEX navigation."""
    allowed = set(paths)
    visited = set()
    queue = [index_path]
    while queue:
        relative = queue.pop()
        if relative in visited or relative not in allowed:
            continue
        visited.add(relative)
        source = resolve_safe_child(layout.project_root, relative)
        if source.name != "INDEX.md" or not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        for link in index_links(text):
            try:
                target = resolve_reference(layout, source, link)
                if target is not None:
                    queue.append(target.relative_to(layout.project_root).as_posix())
            except ValueError:
                continue  # validate_links reports unsafe references separately.
    return [ValidationIssue("VR109", f"Rule is missing from INDEX navigation: {path}", path)
            for path in sorted(allowed - visited)]


def build_load_bundle(inspection, *, domains=(), rules=()):
    from .validation import build_runtime_context, BUDGETS
    context = build_runtime_context(inspection, requested_domains=domains)
    if context["blocked"]:
        raise ValueError("Context is blocked; run its diagnostic command first")
    layout = inspection.layout
    allowed = set(context["load"]["core"]) | set(context["load"]["indexes"])
    for domain in context["routes"]:
        value = inspection.state["domains"][domain]
        allowed.update(f"{layout.rulers_dir}/{value['target_dir']}/{name}" for name in value.get("required_files", [])
                       if rule_owner(f"{value['target_dir']}/{name}", inspection.state["domains"]) == domain)
    queue = list(context["load"]["core"]) + list(context["load"]["indexes"])
    for rule in rules:
        relative = rule if rule.startswith(layout.rulers_dir + "/") else f"{layout.rulers_dir}/{rule}"
        if relative not in allowed:
            raise ValueError(f"Rule is not in the selected active domain: {rule}")
        queue.append(relative)
    selected = {}
    while queue:
        relative = queue.pop(0)
        if relative in selected:
            continue
        source = resolve_safe_child(layout.project_root, relative)
        text = source.read_text(encoding="utf-8")
        selected[relative] = text
        dependencies, _ = references(text)
        for value in dependencies:
            target = resolve_reference(layout, source, value)
            if target is None or target.name in {"AGENTS.md", "RULERS_STATE.json"}:
                continue
            dependency = target.relative_to(layout.project_root).as_posix()
            if dependency not in allowed:
                raise ValueError(f"Dependency outside active selection: {dependency}; select its domain")
            queue.append(dependency)
    if context["profile"]["path"]:
        source = resolve_safe_child(layout.project_root, context["profile"]["path"])
        selected[context["profile"]["path"]] = select_profile_sections(
            source.read_text(encoding="utf-8"), scopes=set(context["profile"]["scopes"]),
            always_sections=context["profile"]["always_sections"],
        )
    total = sum(len(text.encode("utf-8")) for text in selected.values())
    return {"files": list(selected), "available_rules": sorted(allowed), "bytes": total, "within_budget": total <= BUDGETS["fixed_chain_bytes"],
            "content": "\n\n".join(f"<!-- {name} -->\n{text}" for name, text in selected.items())}
