from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .domains import expand_reverse_dependencies, load_domain_registry, rule_owner
from .issues import ValidationIssue
from .paths import RulersLayout, UnsafeRulersPathError, resolve_layout
from .root_entry import has_valid_managed_block
from .state import classify_state_schema, file_sha256, read_state, validate_state
from .transactions import find_incomplete_transaction
from .mutations import CURRENT_ID


TEMPLATE_ARTIFACT_NAMES = {
    "PROJECT_PROFILE.template.md",
    "CHANGELOG.template.md",
}
TEMPLATE_RESIDUE_PATTERNS = (
    ("VR030", re.compile(r"\{\{RULERS_DIR\}\}"), "Unexpanded RULERS_DIR placeholder"),
    ("VR031", re.compile(r"(?m)^##\s*AI_FILL|\[AI_FILL\]"), "AI_FILL residue"),
)
FENCED_YAML_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
RUNTIME_ENTRY_TEMPLATES = {"AGENTS.md.tmpl", "INDEX.md.tmpl"}
RUNTIME_VIRTUAL_FILES = {
    "AGENTS.md": "AGENTS.md.tmpl",
    "INDEX.md": "INDEX.md.tmpl",
    "PROJECT_PROFILE.md": "PROJECT_PROFILE.md.tmpl",
}

BUDGETS = {
    "skill_lines": 105,
    "root_block_bytes": 800,
    "runtime_agents_bytes": 2400,
    "seed_profile_bytes": 1192,
    "core_pair_bytes": 4096,
    "context_bytes": 2000,
    "fixed_chain_bytes": 16000,
    "cli_summary_bytes": 2000,
}

_CONTEXT_SCHEMA_VERSION = 1
_PROFILE_ALWAYS_SECTIONS = ["项目身份", "命令"]
_PROFILE_SCOPED_SECTIONS = ["当前有效事实与约束", "阻塞性未决问题"]


@dataclass(frozen=True)
class ProjectInspection:
    layout: RulersLayout
    state: dict[str, Any] | None
    issues: tuple[ValidationIssue, ...]
    transaction_blocking: bool = False
    profile_valid: bool = True
    global_blocked: bool = False
    schema_classification: str = "current"
    invalid_domains: frozenset[str] = field(default_factory=frozenset)

def _metadata_list(block: str, key: str) -> list[str] | None:
    values: list[str] = []
    found = False
    collecting = False
    for line in block.splitlines():
        stripped = line.strip()
        if stripped == f"{key}:":
            found = True
            collecting = True
            continue
        if stripped == f"{key}: []":
            found = True
            collecting = False
            continue
        if collecting and stripped.startswith("- "):
            value = stripped[2:].split("#", 1)[0].strip().strip("\"'")
            if value:
                values.append(value)
            continue
        if collecting and stripped and not stripped.startswith("- "):
            collecting = False
    return values if found else None


def _runtime_target(runtime_root: Path, source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("\"'")
    prefix = "{{RULERS_DIR}}/"
    if target == "{{RULERS_DIR}}/RULERS_STATE.json":
        return None
    if target.startswith(prefix):
        relative = target[len(prefix):]
        relative = RUNTIME_VIRTUAL_FILES.get(relative, relative)
        direct = runtime_root / relative
        if direct.is_file():
            return direct
        return runtime_root / "domains" / relative
    relative = Path(target)
    if relative.is_absolute() or ".." in relative.parts:
        return runtime_root / "__invalid_metadata_target__"
    return source.parent / relative


def validate_rule_metadata_text(text: str, path: str) -> list[ValidationIssue]:
    match = FENCED_YAML_RE.search(text)
    block = match.group(1) if match else None
    required = ("applies_to", "trigger_keywords", "must_load_with")
    if block is None or any(_metadata_list(block, key) is None for key in required):
        return [
            ValidationIssue(
                "VR106",
                "Runtime rule is missing complete fenced YAML metadata.",
                path,
            )
        ]
    return []


def _validate_runtime_metadata(runtime_root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    files = sorted(
        path
        for path in runtime_root.rglob("*")
        if path.is_file() and (path.suffix == ".md" or path.name.endswith(".md.tmpl"))
    )
    for path in files:
        if path.name in RUNTIME_ENTRY_TEMPLATES:
            continue
        text = path.read_text(encoding="utf-8")
        match = FENCED_YAML_RE.search(text)
        block = match.group(1) if match else None
        metadata_issues = validate_rule_metadata_text(
            text,
            str(path.relative_to(runtime_root.parent.parent)),
        )
        if metadata_issues:
            issues.extend(metadata_issues)
            continue
        for target in _metadata_list(block, "must_load_with") or []:
            resolved = _runtime_target(runtime_root, path, target)
            if resolved is not None and not resolved.is_file():
                issues.append(
                    ValidationIssue(
                        "VR107",
                        "Runtime metadata contains a broken must_load_with reference.",
                        f"{path.relative_to(runtime_root)} -> {target}",
                    )
                )
    return issues


def _load_json(path: Path, code: str, message: str) -> tuple[dict[str, Any] | None, list[ValidationIssue]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as exc:
        return None, [ValidationIssue(code, f"{message}: {exc}", str(path))]


def validate_template(skill_root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    required = (
        skill_root / "SKILL.md",
        skill_root / "templates" / "domain-registry.json",
        skill_root / "templates" / "runtime" / "AGENTS.md.tmpl",
        skill_root / "templates" / "runtime" / "INDEX.md.tmpl",
        skill_root / "templates" / "runtime" / "PROJECT_PROFILE.md.tmpl",
    )
    for path in required:
        if not path.is_file():
            issues.append(ValidationIssue("VR100", "Required Skill resource is missing.", str(path)))
    try:
        registry = load_domain_registry(skill_root)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        issues.append(ValidationIssue("VR101", f"Invalid domain registry: {exc}"))
    else:
        for domain in ("core", "security", "delivery"):
            if domain not in registry:
                issues.append(
                    ValidationIssue("VR102", f"Domain registry is missing '{domain}'.")
                )
        runtime_root = skill_root / "templates" / "runtime"
        for domain, config in registry.items():
            template_root = runtime_root / config.get("template_root", "")
            for filename in config.get("templates", []):
                template_path = template_root / filename
                if not template_path.is_file():
                    issues.append(
                        ValidationIssue(
                            "VR104",
                            f"Registered domain template is missing for '{domain}'.",
                            str(template_path.relative_to(skill_root)),
                        )
                    )
        skill_lines = (skill_root / "SKILL.md").read_text(encoding="utf-8").splitlines()
        if len(skill_lines) > BUDGETS["skill_lines"]:
            issues.append(
                ValidationIssue(
                    "VR105",
                    "SKILL.md exceeds the configured orchestration budget.",
                    "SKILL.md",
                )
            )
        header = (runtime_root / "AGENTS.md.tmpl").read_text(encoding="utf-8")
        if not re.search(r"^> Version: \{\{RELEASE_VERSION\}\}。", header, re.MULTILINE):
            issues.append(ValidationIssue("VR110", "Entry version must use {{RELEASE_VERSION}}, not a manually maintained version.", "templates/runtime/AGENTS.md.tmpl"))
        issues.extend(_validate_runtime_metadata(runtime_root))
        from .root_entry import managed_block
        sizes = {
            "root_block_bytes": len(managed_block("documents/rulers").encode("utf-8")),
            "runtime_agents_bytes": len((runtime_root / "AGENTS.md.tmpl").read_bytes()),
            "seed_profile_bytes": len((runtime_root / "PROJECT_PROFILE.md.tmpl").read_bytes()),
            "core_pair_bytes": sum(len((runtime_root / "core" / name).read_bytes()) for name in ("HARD_CONSTRAINTS.md", "WORKFLOW.md")),
        }
        for key, size in sizes.items():
            if size > BUDGETS[key]:
                issues.append(ValidationIssue("VR108", f"{key} exceeds budget: {size} > {BUDGETS[key]}", key))
    for path in skill_root.rglob("*"):
        if path.is_file() and path.name in {".DS_Store"}:
            issues.append(
                ValidationIssue(
                    "VR103",
                    "Skill source contains an ignored platform artifact.",
                    str(path.relative_to(skill_root)),
                    severity="warning",
                )
            )
    return issues



def _scope_for_managed_path(relative: str, state: dict[str, Any] | None) -> str | None:
    """Determine scope for a managed file path based on State domains."""
    if not state:
        return None
    rulers_dir = state.get("rulers_dir", "documents/rulers")
    if relative == "AGENTS.md":
        return "entry"
    if relative.startswith(f"{rulers_dir}/core/"):
        return "core"
    if relative in (f"{rulers_dir}/INDEX.md", f"{rulers_dir}/AGENTS.md"):
        return "entry"
    if "PROJECT_PROFILE" in relative:
        return "profile"
    prefix = rulers_dir + "/"
    return rule_owner(relative[len(prefix):], state.get("domains", {})) if relative.startswith(prefix) else None


def inspect_project(
    *,
    project_root: Path | str,
    rulers_dir: str,
) -> ProjectInspection:
    """Single authoritative project inspection returning structured results."""
    issues: list[ValidationIssue] = []
    try:
        layout = resolve_layout(project_root, rulers_dir)
    except UnsafeRulersPathError as exc:
        issue = ValidationIssue("VR020", str(exc), rulers_dir, scope="core")
        fallback = RulersLayout(project_root=Path(str(project_root)), rulers_dir=rulers_dir)
        return ProjectInspection(
            layout=fallback,
            state=None,
            issues=(issue,),
            global_blocked=True,
        )

    rulers_root = layout.rulers_root
    state_path = rulers_root / "RULERS_STATE.json"

    required_paths = (
        rulers_root / "AGENTS.md",
        rulers_root / "INDEX.md",
        rulers_root / "PROJECT_PROFILE.md",
        rulers_root / "core" / "HARD_CONSTRAINTS.md",
        rulers_root / "core" / "WORKFLOW.md",
        state_path,
    )
    for path in required_paths:
        if not path.is_file():
            scope = "core" if "core/" in str(path) else "entry"
            issues.append(
                ValidationIssue("VR001", "Required runtime file is missing.", str(path), scope=scope)
            )

    state: dict[str, Any] | None = None
    schema_classification = "current"
    if state_path.is_file():
        state, load_issues = _load_json(
            state_path, "VR002", "RULERS_STATE.json is not valid JSON"
        )
        issues.extend(load_issues)
        if state is not None:
            schema_classification = classify_state_schema(state, target_version=3)
            if schema_classification in {"current", "upgrade"}:
                state_issues = validate_state(state)
                issues.extend(state_issues)
                if any(i.code == "VR010" and "must be objects" in i.message for i in state_issues):
                    return ProjectInspection(layout=layout, state=None, issues=tuple(issues), global_blocked=True)
            if schema_classification == "unsupported":
                issues.append(
                    ValidationIssue(
                        "VR061", "State schema is unsupported and requires repair.",
                        str(state_path), scope="core",
                    )
                )
            if state.get("rulers_dir") != layout.rulers_dir:
                issues.append(
                    ValidationIssue(
                        "VR021",
                        "RULERS_STATE rulers_dir does not match the requested directory.",
                        str(state_path), scope="core",
                    )
                )

    root_agents = layout.project_root / "AGENTS.md"
    if not root_agents.is_file() or not has_valid_managed_block(
        root_agents.read_text(encoding="utf-8") if root_agents.is_file() else ""
    ):
        issues.append(
            ValidationIssue(
                "VR022",
                "Project root AGENTS.md is missing a valid ai-rulers-init managed block.",
                str(root_agents), scope="entry",
            )
        )

    if rulers_root.is_dir():
        for artifact in rulers_root.rglob("*"):
            rel = artifact.relative_to(rulers_root)
            if rel.parts and rel.parts[0] in (".plans", ".transactions"):
                continue
            if artifact.is_dir() and artifact.name == "bootstrap":
                issues.append(
                    ValidationIssue(
                        "VR030",
                        "Bootstrap operation manuals must not be installed at runtime.",
                        str(artifact), scope="entry",
                    )
                )
            if artifact.is_file() and artifact.name in TEMPLATE_ARTIFACT_NAMES:
                issues.append(
                    ValidationIssue(
                        "VR030", "Template artifact must not be installed at runtime.",
                        str(artifact), scope="entry",
                    )
                )
            if artifact.is_file() and artifact.suffix in {".md", ".json"}:
                try:
                    text = artifact.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for code, pattern, message in TEMPLATE_RESIDUE_PATTERNS:
                    if pattern.search(text):
                        issues.append(ValidationIssue(code, message, str(artifact), scope="entry"))

    transaction_blocking = False
    try:
        incomplete = find_incomplete_transaction(layout, current_transaction_id=CURRENT_ID.get())
        if incomplete is not None:
            transaction_blocking = True
            issues.append(
                ValidationIssue(
                    "VR060", "Unfinished transaction blocks runtime context.",
                    str(rulers_root / ".transactions"), scope="transaction",
                )
            )
    except Exception:
        transaction_blocking = True
        issues.append(
            ValidationIssue(
                "VR060", "Transaction state cannot be inspected.",
                str(rulers_root / ".transactions"), scope="transaction",
            )
        )

    profile_valid = True
    if state is not None:
        profile_state = state.get("profile") or {}
        if isinstance(profile_state, Mapping) and profile_state.get("status") == "reviewed":
            reviewed_hash = profile_state.get("reviewed_sha256")
            profile_path = rulers_root / "PROJECT_PROFILE.md"
            if not reviewed_hash:
                profile_valid = False
                issues.append(ValidationIssue("VR042", "Reviewed Profile hash is missing; re-review or upgrade.", str(profile_path), scope="profile"))
            elif profile_path.is_file():
                actual_hash = file_sha256(profile_path)
                if actual_hash != reviewed_hash:
                    profile_valid = False
                    issues.append(
                        ValidationIssue(
                            "VR042",
                            "Reviewed PROJECT_PROFILE.md hash does not match State record.",
                            str(profile_path), scope="profile",
                        )
                    )

    invalid_domains: set[str] = {i.scope for i in issues if i.scope not in (None, "core", "entry", "profile", "transaction") and i.severity == "error"}
    if state is not None:
        for relative, metadata in (state.get("managed_files") or {}).items():
            if not isinstance(metadata, Mapping):
                continue
            if metadata.get("ownership") not in {"managed", "project-generated"}:
                continue
            try:
                from .paths import resolve_safe_child
                path = resolve_safe_child(layout.project_root, relative)
            except (ValueError, OSError):
                issues.append(ValidationIssue("VR020", "Unsafe managed path.", relative, scope="core"))
                continue
            expected_hash = metadata.get("rendered_sha256")
            scope = _scope_for_managed_path(relative, state)
            if not path.is_file():
                issues.append(
                    ValidationIssue("VR040", "Managed file is missing.", relative, scope=scope)
                )
                if scope and scope not in ("profile", "entry"):
                    invalid_domains.add(scope)
            elif expected_hash and file_sha256(path) != expected_hash:
                issues.append(
                    ValidationIssue(
                        "VR040",
                        "Managed file content differs from the recorded rendered hash.",
                        relative, scope=scope,
                    )
                )
                if scope and scope not in ("profile", "entry"):
                    invalid_domains.add(scope)

        from .rule_loading import validate_links, validate_index_routes
        for relative, metadata in (state.get("managed_files") or {}).items():
            if not isinstance(metadata, Mapping) or metadata.get("ownership") != "managed" or not relative.endswith(".md"):
                continue
            scope = _scope_for_managed_path(relative, state)
            if scope in ("entry", "profile", None):
                continue
            source = layout.project_root / relative
            if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(layout.rulers_root):
                continue
            found = validate_rule_metadata_text(source.read_text(encoding="utf-8"), relative)
            if not found:
                found = validate_links(layout, paths=[relative])
            for issue in found:
                issues.append(ValidationIssue(issue.code, issue.message, issue.path, scope=scope))
                if scope != "core":
                    invalid_domains.add(scope)
        for domain, domain_state in (state.get("domains") or {}).items():
            if not isinstance(domain_state, Mapping):
                continue
            if domain == "core" or domain_state.get("level", 0) < 2:
                continue
            target_dir = domain_state.get("target_dir", domain)
            owned_paths = []
            for filename in domain_state.get("required_files", ["INDEX.md"]):
                rulers_relative = f"{target_dir}/{filename}"
                if rule_owner(rulers_relative, state["domains"]) != domain:
                    issues.append(ValidationIssue("VR110", "Domain inventory crosses another domain boundary.", rulers_relative, scope=domain))
                    invalid_domains.add(domain)
                    continue
                owned_paths.append(f"{layout.rulers_dir}/{rulers_relative}")
                domain_path = rulers_root / target_dir / filename
                relative = domain_path.relative_to(layout.project_root).as_posix()
                ownership = state.get("managed_files", {}).get(relative, {})
                if not isinstance(ownership, Mapping) or not ownership.get("rendered_sha256"):
                    issues.append(ValidationIssue("VR050", f"Active rule has no bound inventory hash: {relative}", relative, scope=domain))
                    invalid_domains.add(domain)
                if not domain_path.is_file():
                    issues.append(
                        ValidationIssue(
                            "VR050",
                            f"Active domain '{domain}' is missing required runtime file '{filename}'.",
                            str(domain_path), scope=domain,
                        )
                    )
                    invalid_domains.add(domain)
            if all((layout.project_root / path).is_file() for path in owned_paths):
                route_issues = validate_index_routes(layout, index_path=f"{layout.rulers_dir}/{target_dir}/INDEX.md", paths=owned_paths)
                for issue in route_issues:
                    issues.append(ValidationIssue(issue.code, issue.message, issue.path, scope=domain))
                    invalid_domains.add(domain)

    if state is not None and invalid_domains:
        changed = True
        while changed:
            changed = False
            for domain, domain_state in (state.get("domains") or {}).items():
                if not isinstance(domain_state, Mapping):
                    continue
                if domain in invalid_domains:
                    continue
                requires = domain_state.get("requires_active") or []
                if isinstance(requires, (list, tuple)):
                    for dep in requires:
                        if dep in invalid_domains:
                            invalid_domains.add(domain)
                            changed = True
                            break

    global_blocked = transaction_blocking or schema_classification == "unsupported"
    if not global_blocked:
        for issue in issues:
            if issue.scope in ("core", "entry", "transaction") and issue.code in (
                "VR001", "VR002", "VR010", "VR011", "VR012", "VR013", "VR014", "VR015", "VR016", "VR020", "VR021", "VR022", "VR030", "VR031", "VR040", "VR060", "VR061", "VR106", "VR107",
            ):
                global_blocked = True
                break

    return ProjectInspection(
        layout=layout,
        state=state,
        issues=tuple(sorted(issues, key=lambda i: (i.code, i.path or "", i.message))),
        transaction_blocking=transaction_blocking,
        profile_valid=profile_valid,
        global_blocked=global_blocked,
        schema_classification=schema_classification,
        invalid_domains=frozenset(invalid_domains),
    )


def _effective_phase_and_action(inspection: ProjectInspection) -> tuple[str, str]:
    """Derive effective phase and next_action from inspection results."""
    state = inspection.state
    if state is None:
        return ("repair_required", "plan-repair") if inspection.global_blocked else ("uninitialized", "plan-fresh")
    if inspection.schema_classification == "upgrade":
        return "upgrade_required", "plan-upgrade"
    if inspection.schema_classification == "unsupported":
        return "repair_required", "plan-repair"
    if inspection.transaction_blocking:
        return "repair_required", "plan-repair"
    if inspection.global_blocked:
        return "repair_required", "plan-repair"
    if not inspection.profile_valid:
        return "profile_draft", "plan-reconcile"
    if inspection.invalid_domains:
        return "runtime_ready", "plan-repair"
    phase = state.get("phase", "runtime_ready")
    if phase == "repair_required":
        return "repair_required", "plan-repair"
    if phase != "runtime_ready":
        return phase, "plan-resume"
    return "runtime_ready", "none"


def build_runtime_context(
    inspection: ProjectInspection,
    *,
    requested_domains: Sequence[str] = (),
    skill_root: Path | None = None,
) -> dict[str, Any]:
    """Build compact runtime context from inspection results."""
    state = inspection.state
    layout = inspection.layout
    rulers_dir = layout.rulers_dir if layout else "documents/rulers"

    phase, next_action = _effective_phase_and_action(inspection)

    profile_status = "reviewed" if inspection.profile_valid else "draft"
    if state:
        ps = state.get("profile") or {}
        if isinstance(ps, Mapping):
            profile_status = ps.get("status", profile_status)
        if not inspection.profile_valid:
            profile_status = "draft"
    profile_path = f"{rulers_dir}/PROJECT_PROFILE.md"

    available: list[str] = []
    routes: dict[str, dict[str, Any]] = {}
    level3_ready: list[str] = []
    if state and not inspection.global_blocked and inspection.profile_valid and profile_status == "reviewed":
        for domain, domain_state in sorted((state.get("domains") or {}).items()):
            if not isinstance(domain_state, Mapping):
                continue
            if domain == "core":
                continue
            if domain_state.get("level", 0) < 2:
                continue
            if domain_state.get("review_status") != "reviewed":
                continue
            if domain in inspection.invalid_domains:
                continue
            available.append(domain)
            target_dir = domain_state.get("target_dir", domain)
            index_path = f"{rulers_dir}/{target_dir}/INDEX.md"
            routes[domain] = {"level": domain_state.get("level", 2), "index": index_path}
            if domain_state.get("level3_ready") or domain_state.get("readiness_level", 0) >= 3:
                level3_ready.append(domain)

    unknown = set(requested_domains) - set(state.get("domains", {})) if state else set()
    if unknown:
        raise ValueError("Unknown domain selection: " + ", ".join(sorted(unknown)))
    unavailable = set(requested_domains) - set(available)
    requested = set(requested_domains) & set(available)
    if unavailable and next_action == "none":
        next_action = "review-and-activate-domain"
    load_indexes = [routes[d]["index"] for d in sorted(requested) if d in routes]
    profile_scopes = sorted({"core"} | requested)

    core_load = [
        f"{rulers_dir}/core/HARD_CONSTRAINTS.md",
        f"{rulers_dir}/core/WORKFLOW.md",
    ]

    context_issues = [issue.context_dict() for issue in inspection.issues]

    details_command = None
    if next_action != "none":
        details_command = (
            f"python3 {shlex.quote(rulers_dir + '/scripts/validate_rulers.py')}"
            f" --mode runtime --project-root . --rulers-dir {shlex.quote(rulers_dir)} --format json"
        )

    context: dict[str, Any] = {
        "context_schema_version": _CONTEXT_SCHEMA_VERSION,
        "blocked": inspection.global_blocked or not inspection.profile_valid or bool(unavailable),
        "issue_count": len(inspection.issues),
        "phase": phase,
        "profile": {
            "status": profile_status,
            "path": profile_path if profile_status == "reviewed" and not inspection.global_blocked else "",
            "scopes": profile_scopes,
            "selection": "section-and-scope",
            "always_sections": list(_PROFILE_ALWAYS_SECTIONS),
            "scoped_sections": list(_PROFILE_SCOPED_SECTIONS),
        },
        "routes": {d: routes[d] for d in sorted(requested) if d in routes},
        "available_domains": sorted(available),
        "load": {
            "core": core_load,
            "indexes": load_indexes,
        },
        "level3_ready": sorted(level3_ready),
        "issues": context_issues,
        "next_action": next_action,
        "truncated": False,
    }
    if details_command:
        context["details_command"] = details_command
    return context


def runtime_context_json(context: dict[str, Any]) -> bytes:
    """Serialize context to compact JSON within byte budget."""
    budget = BUDGETS["context_bytes"]

    def _serialize(ctx: dict[str, Any]) -> bytes:
        return json.dumps(
            ctx, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    result = _serialize(context)
    if len(result) <= budget:
        return result

    truncated = dict(context)
    truncated["truncated"] = True
    issues = list(truncated.get("issues") or [])
    while len(issues) > 0 and len(_serialize(truncated)) > budget:
        issues = issues[: len(issues) // 2]
        truncated["issues"] = issues
    if len(_serialize(truncated)) <= budget:
        return _serialize(truncated)

    domains = list(truncated.get("available_domains") or [])
    while len(domains) > 0 and len(_serialize(truncated)) > budget:
        domains = domains[: len(domains) // 2]
        truncated["available_domains"] = domains
    if len(_serialize(truncated)) <= budget:
        return _serialize(truncated)

    truncated["issues"] = []
    truncated["available_domains"] = []
    result = _serialize(truncated)
    if len(result) > budget:
        minimal = {"context_schema_version": _CONTEXT_SCHEMA_VERSION, "blocked": True, "phase": "repair_required", "next_action": "narrow-context-request", "truncated": True, "issue_count": context.get("issue_count", 0), "routes": {}, "load": {"core": context["load"]["core"], "indexes": []}}
        return _serialize(minimal)
    return result


def validate_project(
    *,
    mode: str,
    project_root: Path | str,
    rulers_dir: str,
) -> list[ValidationIssue]:
    """Validate project - thin wrapper over inspect_project."""
    inspection = inspect_project(project_root=project_root, rulers_dir=rulers_dir)
    issues = list(inspection.issues)
    if mode == "runtime" and inspection.state is not None:
        state = inspection.state
        if state.get("phase") != "runtime_ready" or (state.get("profile") or {}).get("status") != "reviewed":
            if not any(issue.code == "VR012" for issue in issues):
                issues.append(
                    ValidationIssue(
                        "VR012",
                        "Runtime validation requires a reviewed profile and runtime_ready phase.",
                        str(inspection.layout.rulers_root / "RULERS_STATE.json"),
                    )
                )
    return issues
