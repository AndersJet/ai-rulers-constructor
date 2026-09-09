from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .domains import load_domain_registry, effective_domain_configs, rule_owner
from .paths import resolve_layout
from .state import file_sha256, read_state, state_json, text_sha256, transition_state
from .validation import validate_rule_metadata_text
from .mutations import transactional, write_text


class DomainLifecycleError(ValueError):
    pass


def _render(text: str, rulers_dir: str) -> str:
    return text.replace("{{RULERS_DIR}}", rulers_dir)


def _require_candidate_phase(state: dict[str, Any]) -> None:
    if state.get("phase") not in {"profile_reviewed", "rules_candidate", "runtime_ready"}:
        raise DomainLifecycleError(
            "Domain candidate generation requires a reviewed profile."
        )


def _domain_state(state: dict[str, Any], domain: str) -> dict[str, Any]:
    return state.setdefault("domains", {}).setdefault(
        domain,
        {
            "detected": True,
            "generated": False,
            "review_status": "not_started",
            "level": 0,
            "review": {"reviewed_by": None, "reviewed_at": None, "evidence": None},
        },
    )


def _record_candidate_state(
    *,
    state: dict[str, Any],
    domain: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    domain_state = _domain_state(state, domain)
    domain_state.update(
        {
            "detected": True,
            "generated": True,
            "review_status": "draft",
            "level": 0,
            "review": {"reviewed_by": None, "reviewed_at": None, "evidence": None},
            "readiness_level": config["readiness_level"],
            "required_files": list(config["templates"]),
            "target_dir": config["target_dir"],
            "level3_ready": False,
        }
    )
    if state.get("phase") == "profile_reviewed":
        return transition_state(state, "rules_candidate")
    return state


@transactional
def render_domain_candidate(
    *,
    skill_root: Path,
    project_root: Path,
    rulers_dir: str,
    domain: str,
) -> dict[str, Any]:
    layout = resolve_layout(project_root, rulers_dir)
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_state(state_path)
    _require_candidate_phase(state)
    registry = load_domain_registry(skill_root)
    if domain not in registry or domain == "core":
        raise DomainLifecycleError(f"Unknown or non-renderable domain: {domain}")
    config = registry[domain]
    if config.get("render_mode") != "deterministic":
        raise DomainLifecycleError(
            f"Domain '{domain}' requires project-specific generation; "
            "generate the target files and run register-domain-candidate."
        )
    source_root = skill_root / "templates" / "runtime" / config["template_root"]
    if not source_root.is_dir():
        raise DomainLifecycleError(
            f"Domain '{domain}' requires project-specific generation; no direct runtime pack exists."
        )

    changed_files: list[str] = []
    domain_state = _domain_state(state, domain)
    target_dir = config["target_dir"]
    if domain_state.get("generated") and any(
        metadata.get("project_owned") for path, metadata in state.get("managed_files", {}).items()
        if path.startswith(f"{layout.rulers_dir}/{target_dir}/")
    ):
        return {"domain": domain, "phase": state["phase"], "changed_files": [], "next_action": "rules-maintenance"}
    render_items: list[tuple[str, Path, str, str]] = []
    for filename in state.get("domains", {}).get(domain, {}).get("required_files", config["templates"]):
        source = source_root / filename
        if not source.is_file():
            raise DomainLifecycleError(f"Missing domain template: {source}")
        content = _render(source.read_text(encoding="utf-8"), layout.rulers_dir)
        if "AI_FILL" in content or "{{RULERS_DIR}}" in content:
            raise DomainLifecycleError(
                f"Domain template is not safe for deterministic rendering: {source}"
            )
        destination = layout.rulers_root / target_dir / filename
        relative = str(destination.relative_to(layout.project_root))
        metadata = (state.get("managed_files") or {}).get(relative)
        if destination.is_file():
            if metadata is None or metadata.get("ownership") != "managed":
                raise DomainLifecycleError(
                    f"VR041 unmanaged file conflict; refusing to overwrite: {relative}"
                )
            expected = metadata.get("rendered_sha256")
            if expected and file_sha256(destination) != expected:
                raise DomainLifecycleError(
                    f"VR040 managed file drift detected; refusing to overwrite: {relative}"
                )
        elif metadata and metadata.get("ownership") == "managed":
            raise DomainLifecycleError(f"VR040 managed file is missing: {relative}")
        render_items.append((filename, destination, content, relative))

    has_changes = any(
        not destination.is_file()
        or destination.read_text(encoding="utf-8") != content
        for _, destination, content, _ in render_items
    )
    if not has_changes and domain_state.get("generated"):
        return {"domain": domain, "phase": state["phase"], "changed_files": []}

    for filename, destination, content, relative in render_items:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file() or destination.read_text(encoding="utf-8") != content:
            write_text(destination, content)
            changed_files.append(relative)
        state.setdefault("managed_files", {})[relative] = {
            "template_id": f"domains/{domain}/{filename}",
            "source_sha256": text_sha256(content),
            "rendered_sha256": file_sha256(destination),
            "ownership": "managed",
        }
    state = _record_candidate_state(state=state, domain=domain, config=config)
    state["last_operation"] = {
        "kind": "render-domain-candidate",
        "status": "complete",
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_text(state_path, state_json(state))
    return {"domain": domain, "phase": state["phase"], "changed_files": changed_files}


@transactional
def register_domain_candidate(
    *,
    skill_root: Path,
    project_root: Path,
    rulers_dir: str,
    domain: str,
) -> dict[str, Any]:
    layout = resolve_layout(project_root, rulers_dir)
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_state(state_path)
    _require_candidate_phase(state)
    registry = load_domain_registry(skill_root)
    if domain not in registry or domain == "core":
        raise DomainLifecycleError(f"Unknown or non-registerable domain: {domain}")
    config = registry[domain]
    if config.get("render_mode") != "project-generated":
        raise DomainLifecycleError(
            f"Domain '{domain}' uses deterministic rendering; run render-domain-candidate."
        )

    target_root = layout.rulers_root / config["target_dir"]
    inventory = state.setdefault("managed_files", {})
    registered_files: list[str] = []
    owners = effective_domain_configs(registry, state)
    previous_domain = state.get("domains", {}).get(domain, {})
    required = previous_domain.get("required_files", config["templates"])
    names = sorted(name for name in set(required) | {path.relative_to(target_root).as_posix() for path in target_root.rglob("*.md")}
                   if rule_owner(f"{config['target_dir']}/{name}", owners) == domain)
    changed = set(names) != set(required)
    for filename in names:
        path = target_root / filename
        if path.is_symlink() or path.resolve() != path:
            raise DomainLifecycleError("Unsafe candidate path")
        if not path.is_file():
            raise DomainLifecycleError(
                f"VR050 project-generated domain '{domain}' is missing: {path}"
            )
        content = path.read_text(encoding="utf-8")
        if "AI_FILL" in content or "{{RULERS_DIR}}" in content:
            raise DomainLifecycleError(
                f"Domain candidate contains template residue: {path}"
            )
        metadata_issues = validate_rule_metadata_text(content, str(path))
        if metadata_issues:
            issue = metadata_issues[0]
            raise DomainLifecycleError(f"{issue.code} {issue.message}: {path}")
        relative = str(path.relative_to(layout.project_root))
        current_hash = file_sha256(path)
        previous = inventory.get(relative) or {}
        if previous.get("rendered_sha256") != current_hash or previous.get("template_id") != f"generated/{domain}/{filename}":
            changed = True
        inventory[relative] = {
            "template_id": f"generated/{domain}/{filename}",
            "project_owned": True,
            "source_sha256": text_sha256(content),
            "rendered_sha256": current_hash,
            "ownership": "managed",
        }
        registered_files.append(relative)

    from .rule_loading import validate_index_routes
    routes = validate_index_routes(layout, index_path=f"{layout.rulers_dir}/{config['target_dir']}/INDEX.md", paths=registered_files)
    if routes:
        raise DomainLifecycleError(routes[0].message)
    domain_state = _domain_state(state, domain)
    if not changed and domain_state.get("generated"):
        return {
            "domain": domain,
            "phase": state["phase"],
            "registered_files": registered_files,
        }
    state = _record_candidate_state(state=state, domain=domain, config={**config, "templates": names})
    state["last_operation"] = {
        "kind": "register-domain-candidate",
        "status": "complete",
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }
    write_text(state_path, state_json(state))
    return {
        "domain": domain,
        "phase": state["phase"],
        "registered_files": registered_files,
    }


@transactional
def activate_domain(
    *,
    skill_root: Path,
    project_root: Path,
    rulers_dir: str,
    domain: str,
    reviewed_by: str,
    evidence: str,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    if not reviewed_by.strip() or not evidence.strip():
        raise DomainLifecycleError("Domain activation requires reviewer and evidence.")
    layout = resolve_layout(project_root, rulers_dir)
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_state(state_path)
    from .validation import inspect_project
    inspection = inspect_project(project_root=layout.project_root, rulers_dir=layout.rulers_dir)
    if inspection.global_blocked or not inspection.profile_valid or domain in inspection.invalid_domains:
        raise DomainLifecycleError("Repair or re-review project facts before activation")
    if state.get("phase") not in {"rules_candidate", "runtime_ready"}:
        raise DomainLifecycleError("Domain activation requires rules_candidate phase.")
    registry = load_domain_registry(skill_root)
    if domain not in registry:
        raise DomainLifecycleError(f"Unknown domain: {domain}")
    domain_state = state.get("domains", {}).get(domain)
    if not domain_state or not domain_state.get("generated"):
        raise DomainLifecycleError(f"Domain '{domain}' has no generated candidate rules.")
    if domain == "delivery":
        security = state.get("domains", {}).get("security") or {}
        if security.get("review_status") != "reviewed" or security.get("level", 0) < 2:
            raise DomainLifecycleError(
                "delivery activation requires the security domain to be reviewed and Level 2."
            )
    target_root = layout.rulers_root / domain_state.get(
        "target_dir", registry[domain]["target_dir"]
    )
    for filename in domain_state.get("required_files", registry[domain]["templates"]):
        path = target_root / filename
        relative = str(path.relative_to(layout.project_root))
        metadata = (state.get("managed_files") or {}).get(relative) or {}
        if not path.is_file():
            raise DomainLifecycleError(f"VR050 active domain file is missing: {relative}")
        if metadata.get("ownership") != "managed":
            raise DomainLifecycleError(f"VR041 domain file is not managed: {relative}")
        if metadata.get("rendered_sha256") != file_sha256(path):
            raise DomainLifecycleError(f"VR040 domain file drift detected: {relative}")
    timestamp = reviewed_at or datetime.now(timezone.utc).astimezone().isoformat()
    domain_state["review_status"] = "reviewed"
    domain_state["level"] = 2
    domain_state["review"] = {
        "reviewed_by": reviewed_by.strip(),
        "reviewed_at": timestamp,
        "evidence": evidence.strip(),
    }
    domain_state["readiness_level"] = registry[domain]["readiness_level"]
    domain_state["level3_ready"] = registry[domain]["readiness_level"] == 3
    state["last_operation"] = {
        "kind": "activate-domain",
        "status": "complete",
        "updated_at": timestamp,
    }
    write_text(state_path, state_json(state))
    return {
        "domain": domain,
        "level": domain_state["level"],
        "level3_ready": domain_state["level3_ready"],
    }
