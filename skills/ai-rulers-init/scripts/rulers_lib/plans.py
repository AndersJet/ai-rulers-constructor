from __future__ import annotations

import copy
import difflib
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .domains import detect_domains, expand_reverse_dependencies, load_domain_registry
from .issues import ValidationIssue
from .paths import RulersLayout, UnsafeRulersPathError, resolve_layout
from .policies import load_policy
from .reconcile import (
    ProfileChange,
    affected_domains,
    diff_profiles,
    domain_actions,
    parse_profile,
)
from .state import classify_state_schema, file_sha256
from .version import RELEASE_VERSION
from .transactions import (
    TransactionSnapshot,
    inspect_incomplete_transaction_evidence,
)


PLAN_SCHEMA_VERSION = 2
PLAN_OPERATIONS = frozenset({"fresh", "resume", "reconcile", "upgrade", "repair", "noop"})

_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLAN_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")
_SNAPSHOT_REF_PATTERN = re.compile(r"^snapshots/[0-9]{6}\.bin$")
_DOMAIN_ACTIONS = frozenset({"keep", "downgrade", "draft", "retire"})
_SAFE_PHASES = frozenset(
    {
        "planned",
        "profile_draft",
        "profile_reviewed",
        "rules_candidate",
        "runtime_ready",
        "repair_required",
    }
)
_TOP_LEVEL_FIELDS = frozenset(
    "plan_schema_version plan_id plan_sha256 operation project_root rulers_dir "
    "template preconditions candidate_profile changes affected_domains domain_actions "
    "file_actions repair_resolutions requires_review review_binding expected_phase "
    "validation detail_references".split()
)
_PRECONDITION_FIELDS = frozenset(
    "state reviewed_profile root_agents claude template_fingerprint policy operation_inputs "
    "transaction_evidence read_set write_set".split()
)
_OPERATION_INPUT_FIELDS = frozenset({"changed_paths", "retired_domains"})
_TRANSACTION_EVIDENCE_FIELDS = frozenset(
    {
        "incomplete_present",
        "transaction_id",
        "lock_nonce",
        "artifacts",
        "requires_replan",
    }
)
_TRANSACTION_ARTIFACT_ROLES = frozenset(
    {"maintenance_lock", "recovery_lease", "recovery_marker", "journal"}
)


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_plan_sha256(plan: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in plan.items()
        if key not in {"plan_id", "plan_sha256"}
    }
    return _sha256_bytes(_canonical_json(payload))


def finalize_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(payload))
    result.pop("plan_id", None)
    result.pop("plan_sha256", None)
    digest = canonical_plan_sha256(result)
    result["plan_id"] = digest.removeprefix("sha256:")[:16]
    result["plan_sha256"] = digest
    return result


def _tree_fingerprint(skill_root: Path) -> str:
    digest = hashlib.sha256()
    roots = (skill_root / "templates", skill_root / "scripts")
    files = sorted(
        path
        for root in roots
        if root.is_dir()
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )
    for path in files:
        relative = path.relative_to(skill_root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return "sha256:" + digest.hexdigest()


def _policy_fact(skill_root: Path, policy_id: str) -> dict[str, str]:
    policy = load_policy(skill_root, policy_id)
    path = skill_root / "templates" / "policies" / f"{policy_id}.json"
    return {"id": str(policy["id"]), "fingerprint": file_sha256(path)}


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _reject_project_internal_symlinks(
    project_root: Path,
    supplied: Path,
    *,
    label: str,
) -> None:
    chain: list[Path] = []
    current = supplied
    while current != current.parent and current.resolve(strict=False) != project_root:
        chain.append(current)
        current = current.parent
    if current.resolve(strict=False) != project_root:
        return
    for component in reversed(chain):
        if component.is_symlink():
            raise ValueError(f"{label} contains a symbolic-link component: {supplied}")


def _relative_path(project_root: Path, path: Path, *, label: str) -> tuple[Path, str]:
    supplied = path.expanduser()
    if not supplied.is_absolute():
        if ".." in supplied.parts:
            raise ValueError(f"{label} must not escape the project root: {path}")
        supplied = project_root / supplied
    _reject_project_internal_symlinks(project_root, supplied, label=label)
    candidate = supplied.resolve(strict=False)
    try:
        relative = candidate.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"{label} must be a strict child of the project root: {path}") from exc
    if relative == Path(".") or ".." in relative.parts:
        raise ValueError(f"{label} must be a strict child of the project root: {path}")
    current = project_root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"{label} contains a symbolic-link component: {path}")
    return candidate, relative.as_posix()


def _regular_file_fact(
    project_root: Path,
    path: Path,
    *,
    label: str,
    required: bool = False,
) -> dict[str, str] | None:
    candidate, relative = _relative_path(project_root, path, label=label)
    if not _lexists(candidate):
        if required:
            raise ValueError(f"{label} does not exist: {relative}")
        return None
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {relative}")
    return {"path": relative, "sha256": file_sha256(candidate)}


def _current_input_fact(
    project_root: Path,
    value: Mapping[str, Any],
    *,
    label: str,
) -> dict[str, str]:
    path = value.get("path")
    expected_hash = value.get("sha256")
    if (
        set(value) != {"path", "sha256"}
        or not _is_relative_file_path(path)
        or not isinstance(expected_hash, str)
        or not _HASH_PATTERN.fullmatch(expected_hash)
    ):
        raise ValueError(f"{label} must be a safe path/hash fact.")
    actual = _regular_file_fact(
        project_root,
        Path(path),
        label=label,
        required=True,
    )
    if actual != {"path": path, "sha256": expected_hash}:
        raise ValueError(f"{label} is missing or stale.")
    return actual


def _path_fact(project_root: Path, path: str, *, label: str) -> dict[str, Any]:
    candidate, relative = _relative_path(project_root, Path(path), label=label)
    if not _lexists(candidate):
        return {"path": relative, "sha256": None}
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"{label} must identify a regular non-symlink file: {relative}")
    return {"path": relative, "sha256": file_sha256(candidate)}


def _read_state_fact(state_path: Path, project_root: Path) -> tuple[dict[str, Any] | None, dict[str, str] | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    if not _lexists(state_path):
        return None, None, issues
    try:
        fact = _regular_file_fact(
            project_root,
            state_path,
            label="RULERS_STATE.json",
            required=True,
        )
    except ValueError as exc:
        issues.append(ValidationIssue("PL101", str(exc), "RULERS_STATE.json"))
        return None, None, issues
    assert fact is not None
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        issues.append(
            ValidationIssue(
                "PL102",
                f"RULERS_STATE.json is unreadable or invalid JSON: {type(exc).__name__}.",
                fact["path"],
            )
        )
        return None, fact, issues
    if not isinstance(payload, dict):
        issues.append(ValidationIssue("PL103", "RULERS_STATE.json must contain an object.", fact["path"]))
        return None, fact, issues
    return payload, fact, issues


def _normalized_state_sections(
    state: Mapping[str, Any],
    *,
    layout: RulersLayout,
    registry: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    sections: dict[str, Mapping[str, Any]] = {}

    def issue(field: str, message: str) -> None:
        issues.append(
            ValidationIssue(
                "PL109",
                f"RULERS_STATE.json {field} {message}",
                f"RULERS_STATE.json:{field}",
            )
        )

    required_sections = {
        "profile",
        "policy",
        "domains",
        "managed_files",
        "last_operation",
    }
    for field in (*sorted(required_sections), "template"):
        value = state.get(field)
        if isinstance(value, Mapping):
            sections[field] = value
        else:
            sections[field] = {}
            if field in state or field in required_sections:
                issue(field, "must be an object.")
    if state.get("schema_version") != 3:
        return sections, issues
    if "content_sha256" in sections["profile"] and "reviewed_sha256" not in sections["profile"] and not sections["policy"].get("fingerprint"):
        return sections, issues

    phase = state.get("phase")
    if not isinstance(phase, str) or phase not in _SAFE_PHASES:
        issue("phase", "must be a schema-3 phase string.")
    if state.get("rulers_dir") != layout.rulers_dir:
        issue("rulers_dir", "must match the requested rulers directory.")

    profile = sections["profile"]
    status = profile.get("status")
    if status not in {"draft", "reviewed"}:
        issue("profile.status", "must be draft or reviewed.")
    if status == "reviewed" and not _valid_hash(
        profile.get("reviewed_sha256")
    ):
        issue(
            "profile.reviewed_sha256",
            "must bind the reviewed Profile hash.",
        )

    policy = sections["policy"]
    if not isinstance(policy.get("id"), str) or not policy.get("id"):
        issue("policy.id", "must be a non-empty string.")
    if not _valid_hash(policy.get("fingerprint")):
        issue("policy.fingerprint", "must be a sha256 hash.")

    domains = sections["domains"]
    if not domains:
        issue("domains", "must contain at least core.")
    for domain, value in domains.items():
        if not isinstance(domain, str) or not domain or domain not in registry:
            issue("domains", "contains an unknown or empty domain key.")
        if not isinstance(value, Mapping):
            issue(f"domains.{domain}", "must be an object.")
            continue
        review = value.get("review_status")
        level = value.get("level")
        if not isinstance(review, str):
            issue(
                f"domains.{domain}.review_status",
                "must be a string.",
            )
        if type(level) is not int or not 0 <= level <= 3:
            issue(f"domains.{domain}.level", "must be from 0 to 3.")

    for path, metadata in sections["managed_files"].items():
        if not (
            isinstance(path, str)
            and _is_relative_file_path(path)
            and "\\" not in path
            and PurePosixPath(path).as_posix() == path
            and isinstance(metadata, Mapping)
        ):
            issue(
                "managed_files",
                "must map safe POSIX paths to metadata objects.",
            )
            continue
        if metadata.get("ownership") not in {
            "managed",
            "collaborative",
            "project-generated",
        }:
            issue(f"managed_files.{path}.ownership", "is invalid.")
        if not _valid_hash(metadata.get("rendered_sha256")):
            issue(f"managed_files.{path}.rendered_sha256", "is invalid.")

    last = sections["last_operation"]
    if last.get("status") not in {"in_progress", "complete"}:
        issue(
            "last_operation.status",
            "must be in_progress or complete.",
        )
    if not isinstance(last.get("kind"), str) or not last.get("kind"):
        issue("last_operation.kind", "must be a non-empty string.")
    return sections, issues
def _validate_managed_ownership_target(
    layout: RulersLayout,
    candidate: str,
) -> tuple[Path, str]:
    target, canonical = _relative_path(
        layout.project_root,
        Path(candidate),
        label="managed ownership target",
    )
    try:
        rulers_relative = target.relative_to(layout.rulers_root)
    except ValueError as exc:
        raise ValueError("managed ownership target must be inside the rulers tree") from exc
    if (
        rulers_relative == Path(".")
        or not rulers_relative.parts
        or rulers_relative.parts[0] in {".plans", ".transactions"}
    ):
        raise ValueError("managed ownership target is outside the runtime rulers tree")
    if _lexists(target) and (target.is_symlink() or not target.is_file()):
        raise ValueError("managed ownership target must be a regular non-symlink file")
    return target, canonical


def _sanitized_state_view(
    state: Mapping[str, Any] | None,
    *,
    sections: Mapping[str, Mapping[str, Any]],
    layout: RulersLayout,
    registry: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> tuple[Mapping[str, Any] | None, frozenset[str]]:
    if state is None:
        return None, frozenset()
    sanitized_domains = {
        domain: value
        for domain, value in sections.get("domains", {}).items()
        if isinstance(domain, str)
        and domain
        and domain in registry
        and isinstance(value, Mapping)
    }
    sanitized_managed: dict[str, Mapping[str, Any]] = {}
    for path, metadata in sections.get("managed_files", {}).items():
        if not isinstance(path, str) or not isinstance(metadata, Mapping):
            continue
        ownership = metadata.get("ownership")
        if not isinstance(ownership, str) or ownership not in {
            "managed",
            "collaborative",
            "project-generated",
        }:
            continue
        try:
            target, canonical = _validate_managed_ownership_target(layout, path)
        except (OSError, UnsafeRulersPathError, ValueError) as exc:
            issues.append(
                ValidationIssue(
                    "PL110",
                    f"Managed target is unsafe or unreadable: {type(exc).__name__}.",
                    path,
                )
            )
            continue
        if canonical != path:
            issues.append(
                ValidationIssue(
                    "PL110",
                    "Managed target path is not canonical.",
                    path,
                )
            )
            continue
        if target.exists():
            try:
                file_sha256(target)
            except OSError as exc:
                issues.append(
                    ValidationIssue(
                        "PL110",
                        f"Managed target cannot be read safely: {type(exc).__name__}.",
                        path,
                    )
                )
                continue
        sanitized_managed[path] = metadata
    sanitized = dict(state)
    sanitized["domains"] = sanitized_domains
    sanitized["managed_files"] = sanitized_managed
    return sanitized, frozenset(sanitized_managed)


def _managed_drift(
    state: Mapping[str, Any],
    project_root: Path,
) -> tuple[str, ...]:
    inventory = state.get("managed_files") or {}
    if not isinstance(inventory, Mapping):
        return ("RULERS_STATE.json",)
    drifted: list[str] = []
    for raw_path, metadata in sorted(inventory.items(), key=lambda item: str(item[0])):
        if not isinstance(raw_path, str) or not isinstance(metadata, Mapping):
            drifted.append(str(raw_path))
            continue
        if metadata.get("ownership") != "managed":
            continue
        try:
            candidate, relative = _relative_path(project_root, Path(raw_path), label="managed file")
        except ValueError:
            drifted.append(raw_path)
            continue
        expected = metadata.get("rendered_sha256")
        if (
            not isinstance(expected, str)
            or not _HASH_PATTERN.fullmatch(expected)
            or not candidate.is_file()
            or candidate.is_symlink()
            or file_sha256(candidate) != expected
        ):
            drifted.append(relative)
    return tuple(sorted(set(drifted)))


def _record_drift_issues(
    issues: list[ValidationIssue],
    drifted: Sequence[str],
) -> None:
    existing = {(issue.code, issue.path) for issue in issues}
    for path in sorted(set(drifted)):
        if ("PL112", path) not in existing:
            issues.append(
                ValidationIssue(
                    "PL112",
                    "Managed or reviewed file drift requires an explicit repair resolution.",
                    path,
                )
            )


def _index_hints(
    *,
    layout: RulersLayout,
    registry: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, tuple[str, ...]], list[dict[str, str]]]:
    hints: dict[str, tuple[str, ...]] = {}
    facts: list[dict[str, str]] = []
    applies_pattern = re.compile(r"^\s*applies_to\s*:\s*$")
    item_pattern = re.compile(r"^\s*-\s*['\"]?(.+?)['\"]?\s*$")
    for domain in sorted(registry):
        target_dir = registry[domain].get("target_dir")
        if not isinstance(target_dir, str) or not target_dir:
            continue
        index_path = layout.rulers_root / target_dir / "INDEX.md"
        if not index_path.is_file() or index_path.is_symlink():
            continue
        fact = _regular_file_fact(layout.project_root, index_path, label=f"{domain} INDEX")
        assert fact is not None
        facts.append(fact)
        values: list[str] = []
        collecting = False
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if applies_pattern.match(line):
                collecting = True
                continue
            if not collecting:
                continue
            match = item_pattern.match(line)
            if match:
                values.append(match.group(1).strip())
                continue
            if line.strip():
                break
        if values:
            hints[domain] = tuple(sorted(set(values)))
    return hints, facts


def _state_fingerprints(state: Mapping[str, Any]) -> tuple[str | None, str | None]:
    template = state.get("template") or {}
    policy = state.get("policy") or {}
    template_fingerprint = (
        template.get("fingerprint") if isinstance(template, Mapping) else None
    ) or state.get("template_fingerprint")
    policy_fingerprint = (
        policy.get("fingerprint") if isinstance(policy, Mapping) else None
    ) or state.get("policy_fingerprint")
    return (
        template_fingerprint if isinstance(template_fingerprint, str) else None,
        policy_fingerprint if isinstance(policy_fingerprint, str) else None,
    )


def _derive_operation(
    *,
    incomplete_transaction: bool,
    state_present: bool,
    state: Mapping[str, Any] | None,
    state_issues: Sequence[ValidationIssue],
    legacy_profile: bool,
    unsafe_profile: bool,
    drifted: Sequence[str],
    has_reconcile_input: bool,
    fingerprints_changed: bool,
) -> str:
    if incomplete_transaction:
        return "repair"
    if state_issues or unsafe_profile:
        return "repair"
    if not state_present and legacy_profile:
        return "upgrade"
    if not state_present and not legacy_profile:
        return "fresh"
    assert state is not None
    classification = classify_state_schema(state, target_version=3)
    if classification == "upgrade":
        return "upgrade"
    if classification == "unsupported":
        return "repair"
    if state.get("phase") == "repair_required" or drifted:
        return "repair"
    if has_reconcile_input:
        return "reconcile"
    if fingerprints_changed:
        return "upgrade"
    last_operation = state.get("last_operation")
    last_status = (
        last_operation.get("status") if isinstance(last_operation, Mapping) else None
    )
    if state.get("phase") != "runtime_ready" or last_status == "in_progress":
        return "resume"
    return "noop"


def _change_summaries(changes: Sequence[ProfileChange]) -> list[dict[str, Any]]:
    counts = Counter(change.kind for change in changes)
    scopes_by_kind: dict[str, set[str]] = {kind: set() for kind in counts}
    for change in changes:
        if change.before:
            scopes_by_kind[change.kind].update(change.before.scopes)
        if change.after:
            scopes_by_kind[change.kind].update(change.after.scopes)
    return [
        {"kind": kind, "count": counts[kind], "scopes": sorted(scopes_by_kind[kind])}
        for kind in sorted(counts)
    ]


def _expected_phase(operation: str, state: Mapping[str, Any] | None) -> str:
    safe_phases = {
        "planned",
        "profile_draft",
        "profile_reviewed",
        "rules_candidate",
        "runtime_ready",
        "repair_required",
    }
    current = str((state or {}).get("phase") or "profile_draft")
    if current in {"incremental_pending", "upgrade_pending"}:
        current = "rules_candidate"
    if current not in safe_phases:
        current = "repair_required"
    if operation == "fresh":
        return "profile_draft"
    if operation == "reconcile":
        return current
    if operation == "repair":
        return "repair_required"
    return current


@dataclass(frozen=True)
class _DerivedPlanSemantics:
    operation: str
    changes: tuple[Mapping[str, Any], ...]
    affected_domains: tuple[str, ...]
    domain_actions: Mapping[str, str]
    write_set: tuple[Mapping[str, Any], ...]
    file_actions: tuple[Mapping[str, Any], ...]
    repair_resolutions: Mapping[str, str]
    validation: tuple[Mapping[str, Any], ...]
    requires_review: bool
    review_binding: Mapping[str, str]
    expected_phase: str


def _transaction_evidence(
    inspection: TransactionSnapshot,
) -> dict[str, Any] | None:
    if not inspection.incomplete_present:
        return None
    return {
        "incomplete_present": True,
        "transaction_id": inspection.transaction_id,
        "lock_nonce": inspection.lock_nonce,
        "artifacts": [
            {"role": fact.role, "path": fact.path, "sha256": fact.sha256}
            for fact in inspection.artifacts
        ],
        "requires_replan": inspection.requires_replan,
    }


def _derive_plan_semantics(
    *,
    state_present: bool,
    state: Mapping[str, Any] | None,
    validation_issues: Sequence[ValidationIssue],
    legacy_profile: bool,
    unsafe_profile: bool,
    drifted: Sequence[str],
    fingerprints_changed: bool,
    profile_changes: Sequence[ProfileChange],
    changed_paths: Sequence[str],
    retired_domains: frozenset[str],
    candidate_fact: Mapping[str, Any] | None,
    detected: frozenset[str],
    registry: Mapping[str, Mapping[str, Any]],
    index_hints: Mapping[str, Sequence[str]],
    state_path: str,
    profile_path: str,
    managed_file_paths: frozenset[str],
    write_hashes: Mapping[str, str | None],
    transaction: TransactionSnapshot | None,
    runtime_paths: frozenset[str] = frozenset(),
) -> _DerivedPlanSemantics:
    operation = _derive_operation(
        incomplete_transaction=transaction is not None,
        state_present=state_present,
        state=state,
        state_issues=validation_issues,
        legacy_profile=legacy_profile,
        unsafe_profile=unsafe_profile,
        drifted=drifted,
        has_reconcile_input=bool(
            candidate_fact is not None or changed_paths or retired_domains
        ),
        fingerprints_changed=fingerprints_changed,
    )
    reconcile_affected = affected_domains(
        changes=profile_changes,
        changed_paths=changed_paths,
        registry=registry,
        index_hints=index_hints,
    )
    if operation == "fresh":
        affected = expand_reverse_dependencies(set(detected) | {"core"}, registry)
    elif operation in {"upgrade", "resume", "noop"}:
        affected = frozenset()
    elif operation == "reconcile":
        global_domains = set((state or {}).get("domains", {})) if "core" in reconcile_affected else set()
        affected = expand_reverse_dependencies(
            set(reconcile_affected) | set(retired_domains) | global_domains,
            registry,
        )
    else:
        repair_inputs = set(drifted)
        if transaction is not None:
            repair_inputs.update(action.path for action in transaction.actions)
        affected = affected_domains(
            changes=profile_changes,
            changed_paths=tuple(sorted(repair_inputs)),
            registry=registry,
            index_hints=index_hints,
        ) or frozenset({"core"})
        affected = expand_reverse_dependencies(
            set(affected) | set(retired_domains),
            registry,
        )
    actions = domain_actions(
        state=state or {},
        affected=affected,
        detected=detected | ({"core"} if operation == "fresh" else set()),
        retired=retired_domains,
    )

    if operation == "repair" and transaction is not None:
        write_paths = frozenset(action.path for action in transaction.actions)
        file_actions: list[Mapping[str, Any]] = []
        for inspected in transaction.actions:
            expected_hash = write_hashes.get(inspected.path)
            if inspected.original_existed:
                file_actions.append(
                    {
                        "kind": "restore",
                        "path": inspected.path,
                        "expected_sha256": expected_hash,
                        "snapshot_ref": inspected.snapshot_ref,
                        "snapshot_sha256": inspected.snapshot_sha256,
                    }
                )
            else:
                file_actions.append(
                    {
                        "kind": "delete",
                        "path": inspected.path,
                        "expected_sha256": expected_hash,
                    }
                )
    else:
        if operation == "repair":
            write_paths = frozenset(
                {state_path}
                | {path for path in drifted if path in managed_file_paths}
            )
        elif operation == "fresh":
            write_paths = frozenset({"AGENTS.md", state_path, profile_path} | set(runtime_paths))
        elif operation in {"resume", "upgrade"}:
            write_paths = frozenset({state_path} | set(runtime_paths))
        elif operation == "reconcile":
            write_paths = frozenset(
                {state_path} | ({profile_path} if candidate_fact is not None else set())
            )
        else:
            write_paths = frozenset()
        file_actions = [
            {
                "kind": "update",
                "path": path,
                "expected_sha256": write_hashes.get(path),
            }
            for path in sorted(write_paths)
        ]
    write_set = tuple(
        {"path": path, "sha256": write_hashes.get(path)}
        for path in sorted(write_paths)
    )
    requires_review = operation in {"reconcile", "upgrade", "repair"}
    review_binding = (
        {"candidate_profile_sha256": candidate_fact["sha256"]}
        if operation == "reconcile" and candidate_fact is not None
        else {}
    )
    resolutions: dict[str, str] = {}
    for index, issue in enumerate(
        sorted(
            validation_issues,
            key=lambda value: (value.code, value.path or "", value.message),
        )
    ):
        base = issue.path or f"{issue.code}:{index}"
        key = base
        suffix = 1
        while key in resolutions:
            suffix += 1
            key = f"{base}#{suffix}"
        resolutions[key] = "manual-review"
    return _DerivedPlanSemantics(
        operation=operation,
        changes=tuple(_change_summaries(profile_changes)),
        affected_domains=tuple(sorted(affected)),
        domain_actions=dict(actions),
        write_set=write_set,
        file_actions=tuple(file_actions),
        repair_resolutions=resolutions,
        validation=tuple(
            issue.to_dict()
            for issue in sorted(
                validation_issues,
                key=lambda value: (value.code, value.path or "", value.message),
            )
        ),
        requires_review=requires_review,
        review_binding=review_binding,
        expected_phase=_expected_phase(operation, state),
    )


@dataclass(frozen=True)
class _PlanningStateView:
    raw: Mapping[str, Any] | None
    derivation: Mapping[str, Any] | None
    present: bool
    fact: Mapping[str, str] | None
    issues: tuple[ValidationIssue, ...]
    managed_paths: frozenset[str]
    unsafe_write_paths: frozenset[str]


@dataclass(frozen=True)
class _PlanningFacts:
    layout: RulersLayout
    registry: Mapping[str, Mapping[str, Any]]
    template_fingerprint: str
    runtime_paths: frozenset[str]
    policy: Mapping[str, str]
    state: _PlanningStateView
    existing_profile_fact: Mapping[str, str] | None
    reviewed_profile_fact: Mapping[str, str] | None
    candidate_fact: Mapping[str, Any] | None
    candidate_snapshot: Any
    reviewed_snapshot: Any
    candidate_bytes: bytes | None
    reviewed_bytes: bytes | None
    changed_paths: tuple[str, ...]
    changed_facts: tuple[Mapping[str, str], ...]
    retired_domains: frozenset[str]
    transaction: TransactionSnapshot
    legacy_profile: bool
    unsafe_profile: bool
    drifted: tuple[str, ...]
    fingerprints_changed: bool
    detected_domains: frozenset[str]
    index_hints: Mapping[str, Sequence[str]]
    root_agents_fact: Mapping[str, str] | None
    claude_fact: Mapping[str, str] | None
    read_set: tuple[Mapping[str, Any], ...]
    write_hashes: Mapping[str, str | None]
    state_path: str
    profile_path: str


@dataclass(frozen=True)
class _StateProfileFacts:
    raw_state: Mapping[str, Any] | None
    state_fact: Mapping[str, str] | None
    state_present: bool
    sections: Mapping[str, Mapping[str, Any]]
    derivation_state: Mapping[str, Any] | None
    managed_paths: frozenset[str]
    unsafe_write_paths: frozenset[str]
    issues: tuple[ValidationIssue, ...]
    existing_profile_fact: Mapping[str, str] | None
    reviewed_profile_fact: Mapping[str, str] | None
    reviewed_snapshot: Any
    reviewed_bytes: bytes | None
    legacy_profile: bool
    unsafe_profile: bool
    profile_drift: tuple[str, ...]


@dataclass(frozen=True)
class _OperationFacts:
    changed_facts: tuple[Mapping[str, str], ...]
    candidate_fact: Mapping[str, Any] | None
    candidate_snapshot: Any
    candidate_bytes: bytes | None
    detected: frozenset[str]
    index_hints: Mapping[str, Sequence[str]]
    index_facts: tuple[Mapping[str, str], ...]
    issues: tuple[ValidationIssue, ...]


def _capture_state_profile(
    *,
    layout: RulersLayout,
    registry: Mapping[str, Mapping[str, Any]],
) -> _StateProfileFacts:
    state_file = layout.rulers_root / "RULERS_STATE.json"
    profile_file = layout.rulers_root / "PROJECT_PROFILE.md"
    state, state_fact, issues = _read_state_fact(
        state_file,
        layout.project_root,
    )
    state_present = _lexists(state_file)
    unsafe_paths: set[str] = set()
    if state_present and state_fact is None:
        unsafe_paths.add(
            state_file.relative_to(layout.project_root).as_posix()
        )
    sections: dict[str, Mapping[str, Any]] = {}
    if state is not None:
        sections, shape_issues = _normalized_state_sections(
            state,
            layout=layout,
            registry=registry,
        )
        issues.extend(shape_issues)
    derivation, managed_paths = _sanitized_state_view(
        state,
        sections=sections,
        layout=layout,
        registry=registry,
        issues=issues,
    )

    existing: Mapping[str, str] | None = None
    reviewed: Mapping[str, str] | None = None
    reviewed_snapshot = None
    reviewed_bytes: bytes | None = None
    profile_drift: list[str] = []
    unsafe_profile = False
    legacy_profile = False
    if _lexists(profile_file):
        try:
            existing = _regular_file_fact(
                layout.project_root,
                profile_file,
                label="PROJECT_PROFILE.md",
                required=True,
            )
        except ValueError as exc:
            relative = profile_file.relative_to(
                layout.project_root
            ).as_posix()
            unsafe_paths.add(relative)
            if state_present:
                profile_drift.append(relative)
            else:
                unsafe_profile = True
                issues.append(
                    ValidationIssue("PL104", str(exc), profile_file.name)
                )
        else:
            assert existing is not None
            if not state_present:
                legacy_profile = True
            elif (
                state is not None
                and sections["profile"].get("status") == "reviewed"
            ):
                profile_state = sections["profile"]
                expected = (
                    (profile_state.get("reviewed_sha256") or profile_state.get("content_sha256"))
                    if state.get("schema_version") == 3
                    else profile_state.get("content_sha256")
                )
                if (
                    _valid_hash(expected)
                    and existing["sha256"] == expected
                ):
                    try:
                        reviewed_bytes = profile_file.read_bytes()
                        reviewed_snapshot = parse_profile(
                            reviewed_bytes.decode("utf-8"),
                            allowed_scopes=frozenset(registry),
                        )
                    except (OSError, UnicodeDecodeError, ValueError) as exc:
                        profile_drift.append(existing["path"])
                        issues.append(
                            ValidationIssue(
                                "PL108",
                                "Reviewed PROJECT_PROFILE.md is invalid: "
                                f"{type(exc).__name__}.",
                                existing["path"],
                            )
                        )
                    else:
                        reviewed = existing
                else:
                    profile_drift.append(existing["path"])
    elif (
        state is not None
        and sections["profile"].get("status") == "reviewed"
    ):
        profile_drift.append(
            profile_file.relative_to(layout.project_root).as_posix()
        )
    return _StateProfileFacts(
        raw_state=state,
        state_fact=state_fact,
        state_present=state_present,
        sections=sections,
        derivation_state=derivation,
        managed_paths=managed_paths,
        unsafe_write_paths=frozenset(unsafe_paths),
        issues=tuple(issues),
        existing_profile_fact=existing,
        reviewed_profile_fact=reviewed,
        reviewed_snapshot=reviewed_snapshot,
        reviewed_bytes=reviewed_bytes,
        legacy_profile=legacy_profile,
        unsafe_profile=unsafe_profile,
        profile_drift=tuple(profile_drift),
    )


def _capture_operation_facts(
    *,
    layout: RulersLayout,
    registry: Mapping[str, Mapping[str, Any]],
    candidate_profile: Path | None,
    changed_paths: Sequence[str],
) -> _OperationFacts:
    changed_facts: list[Mapping[str, str]] = []
    for path in changed_paths:
        fact = _regular_file_fact(
            layout.project_root,
            Path(path),
            label="changed path",
            required=True,
        )
        assert fact is not None
        changed_facts.append(fact)
    candidate_fact: Mapping[str, Any] | None = None
    candidate_snapshot = None
    candidate_bytes: bytes | None = None
    if candidate_profile is not None:
        fact = _regular_file_fact(
            layout.project_root,
            candidate_profile,
            label="candidate profile",
            required=True,
        )
        assert fact is not None
        candidate_bytes = (layout.project_root / fact["path"]).read_bytes()
        candidate_snapshot = parse_profile(
            candidate_bytes.decode("utf-8"),
            allowed_scopes=frozenset(registry),
        )
        candidate_fact = {
            **fact,
            "record_count": len(candidate_snapshot.records),
            "unresolved_count": len(candidate_snapshot.unresolved),
        }
    issues: list[ValidationIssue] = []
    try:
        hints, index_facts = _index_hints(
            layout=layout,
            registry=registry,
        )
    except (OSError, UnicodeDecodeError, TypeError, ValueError) as exc:
        hints, index_facts = {}, []
        issues.append(
            ValidationIssue(
                "PL111",
                "Domain INDEX inputs are unsafe or unreadable: "
                f"{type(exc).__name__}.",
            )
        )
    return _OperationFacts(
        changed_facts=tuple(changed_facts),
        candidate_fact=candidate_fact,
        candidate_snapshot=candidate_snapshot,
        candidate_bytes=candidate_bytes,
        detected=frozenset(
            detect_domains(layout.project_root, dict(registry))
        ),
        index_hints=hints,
        index_facts=tuple(index_facts),
        issues=tuple(issues),
    )


def _capture_root_facts(
    layout: RulersLayout,
) -> tuple[
    Mapping[str, str] | None,
    Mapping[str, str] | None,
    tuple[str, ...],
    tuple[ValidationIssue, ...],
]:
    facts: list[Mapping[str, str] | None] = []
    unsafe: list[str] = []
    issues: list[ValidationIssue] = []
    for label, target in (
        ("root AGENTS.md", layout.project_root / "AGENTS.md"),
        ("CLAUDE.md", layout.project_root / "CLAUDE.md"),
    ):
        try:
            fact = _regular_file_fact(
                layout.project_root,
                target,
                label=label,
            )
        except ValueError as exc:
            issues.append(ValidationIssue("PL107", str(exc), target.name))
            unsafe.append(
                target.relative_to(layout.project_root).as_posix()
            )
            fact = None
        facts.append(fact)
    return facts[0], facts[1], tuple(unsafe), tuple(issues)


def _load_planning_policy(
    *,
    skill_root: Path,
    requested: str | None,
    captured: _StateProfileFacts,
    issues: list[ValidationIssue],
) -> Mapping[str, str]:
    recorded = (
        captured.sections["policy"].get("id")
        if captured.raw_state is not None
        else None
    )
    effective = (
        requested
        or (recorded if isinstance(recorded, str) else None)
        or "strict-cn"
    )
    try:
        policy = _policy_fact(skill_root, effective)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if requested is not None:
            raise ValueError(f"Unknown requested policy: {requested}") from exc
        issues.append(
            ValidationIssue(
                "PL108",
                "RULERS_STATE.json policy cannot be loaded: "
                f"{type(exc).__name__}.",
                "RULERS_STATE.json:policy.id",
            )
        )
        policy = _policy_fact(skill_root, "strict-cn")
    if (
        captured.raw_state is not None
        and captured.raw_state.get("schema_version") == 3
        and not isinstance(recorded, str)
    ):
        issues.append(
            ValidationIssue(
                "PL106",
                "RULERS_STATE.json is missing its policy ID.",
            )
        )
    return policy


def _capture_planning_facts(
    *,
    skill_root: Path,
    project_root: Path,
    rulers_dir: str,
    policy_id: str | None,
    candidate_profile: Path | None,
    changed_paths: Sequence[str],
    retired_domains: Sequence[str],
) -> _PlanningFacts:
    layout = resolve_layout(project_root, rulers_dir)
    registry = load_domain_registry(skill_root)
    changed = tuple(sorted(set(changed_paths)))
    retired = frozenset(retired_domains)
    unknown = sorted(retired - registry.keys())
    if unknown:
        raise ValueError("Unknown retired domain(s): " + ", ".join(unknown))

    captured = _capture_state_profile(
        layout=layout,
        registry=registry,
    )
    issues = list(captured.issues)
    transaction = inspect_incomplete_transaction_evidence(layout)
    if transaction.semantic_error is not None:
        issues.append(
            ValidationIssue(
                "PL105",
                "Incomplete transaction cannot be inspected: "
                f"{transaction.semantic_error}.",
            )
        )
    policy = _load_planning_policy(
        skill_root=skill_root,
        requested=policy_id,
        captured=captured,
        issues=issues,
    )
    template = _tree_fingerprint(skill_root)
    drifted = tuple(
        sorted(
            set(
                _managed_drift(
                    captured.derivation_state,
                    layout.project_root,
                )
                if captured.derivation_state is not None
                else ()
            )
            | set(captured.profile_drift)
        )
    )
    _record_drift_issues(issues, drifted)
    recorded_template, recorded_policy = (
        _state_fingerprints(captured.raw_state)
        if captured.raw_state is not None
        else (None, None)
    )
    fingerprints_changed = captured.raw_state is not None and (
        recorded_template != template
        or recorded_policy != policy["fingerprint"]
        or captured.sections["policy"].get("id") != policy["id"]
    )
    operation = _capture_operation_facts(
        layout=layout,
        registry=registry,
        candidate_profile=candidate_profile,
        changed_paths=changed,
    )
    issues.extend(operation.issues)
    agents, claude, root_unsafe, root_issues = _capture_root_facts(
        layout
    )
    issues.extend(root_issues)

    read_map: dict[str, Mapping[str, Any]] = {}
    for fact in (
        captured.state_fact,
        captured.existing_profile_fact,
        agents,
        claude,
        operation.candidate_fact,
        *operation.changed_facts,
        *operation.index_facts,
    ):
        if fact is not None:
            read_map[fact["path"]] = {
                "path": fact["path"],
                "sha256": fact["sha256"],
            }
    evidence = _transaction_evidence(transaction)
    if evidence is not None:
        for fact in evidence["artifacts"]:
            read_map[fact["path"]] = {
                "path": fact["path"],
                "sha256": fact["sha256"],
            }

    state_path = (
        layout.rulers_root / "RULERS_STATE.json"
    ).relative_to(layout.project_root).as_posix()
    profile_path = (
        layout.rulers_root / "PROJECT_PROFILE.md"
    ).relative_to(layout.project_root).as_posix()
    from .runtime_files import runtime_files, retired_runtime_files
    generated = runtime_files(skill_root=skill_root, layout=layout, policy_id=policy["id"], state=captured.raw_state) if not root_unsafe else {}
    retired_files = retired_runtime_files(layout=layout, policy_id=policy["id"], state=captured.raw_state)
    possible_writes = {
        *retired_files,
        *generated,
        "AGENTS.md",
        state_path,
        profile_path,
        *captured.managed_paths,
    } - set(captured.unsafe_write_paths) - set(root_unsafe)
    if transaction.incomplete_present:
        possible_writes.update(action.path for action in transaction.actions)
    write_hashes = {
        path: _path_fact(
            layout.project_root,
            path,
            label="derived write path",
        )["sha256"]
        for path in sorted(possible_writes)
    }
    return _PlanningFacts(
        layout=layout,
        registry=registry,
        template_fingerprint=template,
        runtime_paths=frozenset(generated) | retired_files,
        policy=policy,
        state=_PlanningStateView(
            raw=captured.raw_state,
            derivation=captured.derivation_state,
            present=captured.state_present,
            fact=captured.state_fact,
            issues=tuple(issues),
            managed_paths=captured.managed_paths,
            unsafe_write_paths=(
                captured.unsafe_write_paths | frozenset(root_unsafe)
            ),
        ),
        existing_profile_fact=captured.existing_profile_fact,
        reviewed_profile_fact=captured.reviewed_profile_fact,
        candidate_fact=operation.candidate_fact,
        candidate_snapshot=operation.candidate_snapshot,
        reviewed_snapshot=captured.reviewed_snapshot,
        candidate_bytes=operation.candidate_bytes,
        reviewed_bytes=captured.reviewed_bytes,
        changed_paths=changed,
        changed_facts=operation.changed_facts,
        retired_domains=retired,
        transaction=transaction,
        legacy_profile=captured.legacy_profile,
        unsafe_profile=captured.unsafe_profile,
        drifted=drifted,
        fingerprints_changed=fingerprints_changed,
        detected_domains=operation.detected,
        index_hints=operation.index_hints,
        root_agents_fact=agents,
        claude_fact=claude,
        read_set=tuple(read_map[path] for path in sorted(read_map)),
        write_hashes=write_hashes,
        state_path=state_path,
        profile_path=profile_path,
    )
def _assemble_plan(
    facts: _PlanningFacts,
    *,
    requested_operation: str,
    requested_resolutions: Mapping[str, str],
) -> dict[str, Any]:
    profile_changes: tuple[ProfileChange, ...] = ()
    if (
        facts.candidate_snapshot is not None
        and facts.reviewed_snapshot is not None
    ):
        profile_changes = diff_profiles(
            facts.reviewed_snapshot,
            facts.candidate_snapshot,
        )
    transaction = (
        facts.transaction if facts.transaction.incomplete_present else None
    )
    semantics = _derive_plan_semantics(
        state_present=facts.state.present,
        state=facts.state.derivation,
        validation_issues=facts.state.issues,
        legacy_profile=facts.legacy_profile,
        unsafe_profile=facts.unsafe_profile,
        drifted=facts.drifted,
        fingerprints_changed=facts.fingerprints_changed,
        profile_changes=profile_changes,
        changed_paths=facts.changed_paths,
        retired_domains=facts.retired_domains,
        candidate_fact=facts.candidate_fact,
        detected=facts.detected_domains,
        registry=facts.registry,
        index_hints=facts.index_hints,
        state_path=facts.state_path,
        profile_path=facts.profile_path,
        managed_file_paths=facts.state.managed_paths,
        write_hashes=facts.write_hashes,
        transaction=transaction,
        runtime_paths=facts.runtime_paths,
    )
    operation = semantics.operation
    if requested_operation != "auto" and requested_operation != operation:
        raise ValueError(
            f"Requested operation '{requested_operation}' conflicts with "
            f"detected operation '{operation}'."
        )
    if requested_resolutions:
        allowed = {"restore-managed", "adopt-current", "manual-merge", "manual-review"}
        if operation != "repair" or any(value not in allowed for value in requested_resolutions.values()):
            raise ValueError("Repair resolutions require repair and supported actions.")
        if any(path not in facts.state.managed_paths for path in requested_resolutions):
            raise ValueError("Repair resolution must name a managed file.")
    if semantics.repair_resolutions and operation != "repair":
        raise ValueError(
            "repair_resolutions are only valid for repair plans."
        )
    has_reconcile_input = bool(
        facts.candidate_fact is not None
        or facts.changed_paths
        or facts.retired_domains
    )
    if has_reconcile_input and operation in {
        "upgrade",
        "repair",
        "resume",
        "noop",
    }:
        raise ValueError(
            f"Detected {operation}; complete it and create a new reconcile plan."
        )
    if operation == "fresh" and (
        facts.changed_paths or facts.retired_domains
    ):
        raise ValueError(
            "Fresh plans accept candidate_profile only; "
            "changed_paths and retired_domains require reconcile."
        )
    if operation == "reconcile" and facts.reviewed_profile_fact is None:
        raise ValueError(
            "Reconcile requires a reviewed PROJECT_PROFILE.md "
            "with a matching State hash."
        )
    has_patch = (
        operation == "reconcile"
        and facts.candidate_bytes is not None
        and facts.reviewed_bytes is not None
        and facts.candidate_bytes != facts.reviewed_bytes
    )
    payload = {
        "plan_schema_version": PLAN_SCHEMA_VERSION,
        "operation": operation,
        "project_root": str(facts.layout.project_root),
        "rulers_dir": facts.layout.rulers_dir,
        "template": {
            "version": RELEASE_VERSION,
            "fingerprint": facts.template_fingerprint,
        },
        "preconditions": {
            "state": facts.state.fact,
            "reviewed_profile": facts.reviewed_profile_fact,
            "root_agents": facts.root_agents_fact,
            "claude": facts.claude_fact,
            "template_fingerprint": facts.template_fingerprint,
            "policy": facts.policy,
            "operation_inputs": {
                "changed_paths": [
                    {"path": fact["path"], "sha256": fact["sha256"]}
                    for fact in facts.changed_facts
                ],
                "retired_domains": sorted(facts.retired_domains),
            },
            "transaction_evidence": _transaction_evidence(
                facts.transaction
            ),
            "read_set": list(facts.read_set),
            "write_set": list(semantics.write_set),
        },
        "candidate_profile": facts.candidate_fact,
        "changes": list(semantics.changes),
        "affected_domains": list(semantics.affected_domains),
        "domain_actions": dict(semantics.domain_actions),
        "file_actions": list(semantics.file_actions),
        "repair_resolutions": dict(requested_resolutions or semantics.repair_resolutions),
        "requires_review": semantics.requires_review,
        "review_binding": dict(semantics.review_binding),
        "expected_phase": semantics.expected_phase,
        "validation": list(semantics.validation),
        "detail_references": ["profile.patch"] if has_patch else [],
    }
    return finalize_plan(payload)


def create_plan(
    *,
    skill_root: Path,
    project_root: Path,
    rulers_dir: str,
    policy_id: str | None = None,
    operation: str = "auto",
    candidate_profile: Path | None = None,
    changed_paths: Sequence[str] = (),
    retired_domains: Sequence[str] = (),
    repair_resolutions: Mapping[str, str] | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    if operation != "auto" and operation not in PLAN_OPERATIONS:
        raise ValueError(f"Unknown plan operation: {operation}")
    resolutions = dict(sorted((repair_resolutions or {}).items()))
    if any(
        not isinstance(key, str)
        or not key
        or not isinstance(value, str)
        or not value
        for key, value in resolutions.items()
    ):
        raise ValueError(
            "repair_resolutions must map non-empty strings "
            "to non-empty strings."
        )
    facts = _capture_planning_facts(
        skill_root=skill_root,
        project_root=project_root,
        rulers_dir=rulers_dir,
        policy_id=policy_id,
        candidate_profile=candidate_profile,
        changed_paths=changed_paths,
        retired_domains=retired_domains,
    )
    plan = _assemble_plan(
        facts,
        requested_operation=operation,
        requested_resolutions=resolutions,
    )
    write_plan_bundle(plan, layout=facts.layout, output=output)
    return plan


def _is_relative_file_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path != PurePosixPath(".")


def _detail_contract_error(plan: Mapping[str, Any]) -> str | None:
    details = plan.get("detail_references")
    if details not in ([], ["profile.patch"]):
        return "detail_references must be [] or ['profile.patch']."
    if details == ["profile.patch"]:
        preconditions = plan.get("preconditions")
        if not (
            plan.get("operation") == "reconcile"
            and isinstance(plan.get("candidate_profile"), Mapping)
            and isinstance(preconditions, Mapping)
            and isinstance(preconditions.get("reviewed_profile"), Mapping)
        ):
            return (
                "profile.patch detail reference requires reconcile, candidate_profile, "
                "and reviewed Profile inputs."
            )
    return None


@dataclass(frozen=True)
class _PlanDocument:
    payload: Mapping[str, Any]
    project_root: Path
    rulers_dir: str
    policy_id: str
    candidate_path: Path | None
    changed_paths: tuple[str, ...]
    retired_domains: tuple[str, ...]


def _valid_hash(value: Any, *, nullable: bool = False) -> bool:
    return (nullable and value is None) or (
        isinstance(value, str) and bool(_HASH_PATTERN.fullmatch(value))
    )


def _valid_fact(
    value: Any,
    *,
    nullable_object: bool = True,
    nullable_hash: bool = False,
) -> bool:
    return (
        value is None
        and nullable_object
        or isinstance(value, Mapping)
        and set(value) == {"path", "sha256"}
        and _is_relative_file_path(value.get("path"))
        and _valid_hash(value.get("sha256"), nullable=nullable_hash)
    )


def _valid_fact_list(value: Any, *, nullable_hash: bool) -> bool:
    if not isinstance(value, list) or any(
        not _valid_fact(
            item,
            nullable_object=False,
            nullable_hash=nullable_hash,
        )
        for item in value
    ):
        return False
    paths = [item["path"] for item in value]
    return paths == sorted(set(paths))


def _valid_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and value == sorted(set(value))
    )


def _valid_candidate(value: Any) -> bool:
    return value is None or (
        isinstance(value, Mapping)
        and set(value)
        == {"path", "sha256", "record_count", "unresolved_count"}
        and _valid_fact(
            {"path": value.get("path"), "sha256": value.get("sha256")},
            nullable_object=False,
        )
        and type(value.get("record_count")) is int
        and value["record_count"] >= 0
        and type(value.get("unresolved_count")) is int
        and value["unresolved_count"] >= 0
    )


def _valid_changes(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    kinds: list[str] = []
    for change in value:
        if not (
            isinstance(change, Mapping)
            and set(change) == {"kind", "count", "scopes"}
            and isinstance(change.get("kind"), str)
            and change.get("kind")
            and type(change.get("count")) is int
            and change["count"] > 0
            and _valid_string_list(change.get("scopes"))
        ):
            return False
        kinds.append(change["kind"])
    return kinds == sorted(set(kinds))


def _valid_file_actions(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    paths: list[str] = []
    for action in value:
        if not isinstance(action, Mapping):
            return False
        kind = action.get("kind")
        keys = (
            {
                "kind",
                "path",
                "expected_sha256",
                "snapshot_ref",
                "snapshot_sha256",
            }
            if kind == "restore"
            else {"kind", "path", "expected_sha256"}
        )
        if not (
            kind in {"update", "restore", "delete"}
            and set(action) == keys
            and _is_relative_file_path(action.get("path"))
            and _valid_hash(
                action.get("expected_sha256"),
                nullable=kind != "delete",
            )
        ):
            return False
        if kind == "restore" and not (
            isinstance(action.get("snapshot_ref"), str)
            and _SNAPSHOT_REF_PATTERN.fullmatch(action["snapshot_ref"])
            and _valid_hash(action.get("snapshot_sha256"))
        ):
            return False
        paths.append(action["path"])
    return len(paths) == len(set(paths))


def _valid_transaction_evidence(value: Any) -> bool:
    if value is None:
        return True
    if not (
        isinstance(value, Mapping)
        and set(value) == _TRANSACTION_EVIDENCE_FIELDS
        and value.get("incomplete_present") is True
        and type(value.get("requires_replan")) is bool
        and (
            value.get("transaction_id") is None
            or isinstance(value.get("transaction_id"), str)
        )
        and (
            value.get("lock_nonce") is None
            or isinstance(value.get("lock_nonce"), str)
        )
        and isinstance(value.get("artifacts"), list)
    ):
        return False
    paths: list[str] = []
    for artifact in value["artifacts"]:
        if not (
            isinstance(artifact, Mapping)
            and set(artifact) == {"role", "path", "sha256"}
            and artifact.get("role") in _TRANSACTION_ARTIFACT_ROLES
            and _valid_fact(
                {
                    "path": artifact.get("path"),
                    "sha256": artifact.get("sha256"),
                },
                nullable_object=False,
            )
        ):
            return False
        paths.append(artifact["path"])
    return len(paths) == len(set(paths))


def _valid_validation(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, Mapping)
        and set(item) in (
            {"code", "message", "path", "severity"},
            {"code", "message", "path", "severity", "scope"},
        )
        and isinstance(item.get("code"), str)
        and isinstance(item.get("message"), str)
        and (
            item.get("path") is None
            or isinstance(item.get("path"), str)
        )
        and item.get("severity") == "error"
        and (
            item.get("scope") is None
            or isinstance(item.get("scope"), str)
        )
        for item in value
    )


def _require_shape(
    issues: list[ValidationIssue],
    condition: bool,
    code: str,
    message: str,
    path: str | None = None,
) -> None:
    if not condition:
        issues.append(ValidationIssue(code, message, path))


def _decode_plan_identity(
    plan: Mapping[str, Any],
    issues: list[ValidationIssue],
) -> tuple[Path | None, str | None]:
    _require_shape(
        issues,
        set(plan) == _TOP_LEVEL_FIELDS,
        "PL002",
        "Plan must contain exactly the 19 schema fields.",
    )
    _require_shape(
        issues,
        plan.get("plan_schema_version") == PLAN_SCHEMA_VERSION,
        "PL003",
        "Unsupported plan schema version.",
    )
    _require_shape(
        issues,
        isinstance(plan.get("operation"), str)
        and plan.get("operation") in PLAN_OPERATIONS,
        "PL004",
        "operation is invalid.",
        "operation",
    )
    project_value = plan.get("project_root")
    project_root = (
        Path(project_value)
        if isinstance(project_value, str) and project_value
        else None
    )
    _require_shape(
        issues,
        project_root is not None and project_root.is_absolute(),
        "PL005",
        "project_root must be an absolute path string.",
        "project_root",
    )
    rulers_dir = plan.get("rulers_dir")
    _require_shape(
        issues,
        _is_relative_file_path(rulers_dir),
        "PL006",
        "rulers_dir must be project-relative.",
        "rulers_dir",
    )
    template = plan.get("template")
    _require_shape(
        issues,
        isinstance(template, Mapping)
        and set(template) == {"version", "fingerprint"}
        and isinstance(template.get("version"), str)
        and _valid_hash(template.get("fingerprint")),
        "PL007",
        "template must contain version and fingerprint.",
        "template",
    )
    return project_root, rulers_dir if isinstance(rulers_dir, str) else None


def _decode_plan_inputs(
    plan: Mapping[str, Any],
    issues: list[ValidationIssue],
) -> tuple[str | None, Path | None, tuple[str, ...], tuple[str, ...]]:
    preconditions = plan.get("preconditions")
    if not (
        isinstance(preconditions, Mapping)
        and set(preconditions) == _PRECONDITION_FIELDS
    ):
        _require_shape(
            issues,
            False,
            "PL008",
            "preconditions has an invalid shape.",
            "preconditions",
        )
        return None, None, (), ()
    _require_shape(
        issues,
        all(
            _valid_fact(preconditions.get(name))
            for name in (
                "state",
                "reviewed_profile",
                "root_agents",
                "claude",
            )
        ),
        "PL011",
        "named precondition must be a safe path/hash object.",
        "preconditions",
    )
    _require_shape(
        issues,
        _valid_hash(preconditions.get("template_fingerprint")),
        "PL015",
        "template_fingerprint must be a hash.",
        "preconditions.template_fingerprint",
    )
    policy = preconditions.get("policy")
    policy_shape = (
        isinstance(policy, Mapping)
        and set(policy) == {"id", "fingerprint"}
        and isinstance(policy.get("id"), str)
        and bool(policy.get("id"))
        and _valid_hash(policy.get("fingerprint"))
    )
    _require_shape(
        issues,
        policy_shape,
        "PL016",
        "policy must contain an id and fingerprint.",
        "preconditions.policy",
    )
    inputs = preconditions.get("operation_inputs")
    input_shape = (
        isinstance(inputs, Mapping)
        and set(inputs) == _OPERATION_INPUT_FIELDS
    )
    _require_shape(
        issues,
        input_shape,
        "PL017",
        "operation_inputs has an invalid shape.",
        "preconditions.operation_inputs",
    )
    changed_paths: tuple[str, ...] = ()
    retired_domains: tuple[str, ...] = ()
    if input_shape:
        changed = inputs.get("changed_paths")
        retired = inputs.get("retired_domains")
        changed_valid = _valid_fact_list(changed, nullable_hash=False)
        retired_valid = _valid_string_list(retired)
        _require_shape(
            issues,
            changed_valid,
            "PL018",
            "changed_paths must be sorted path/hash facts.",
            "preconditions.operation_inputs.changed_paths",
        )
        _require_shape(
            issues,
            retired_valid,
            "PL019",
            "retired_domains must be sorted unique strings.",
            "preconditions.operation_inputs.retired_domains",
        )
        if changed_valid:
            changed_paths = tuple(item["path"] for item in changed)
        if retired_valid:
            retired_domains = tuple(retired)
    _require_shape(
        issues,
        _valid_transaction_evidence(
            preconditions.get("transaction_evidence")
        ),
        "PL020",
        "transaction evidence has an invalid shape or artifacts.",
        "preconditions.transaction_evidence",
    )
    for name, nullable_hash, code in (
        ("read_set", False, "PL021"),
        ("write_set", True, "PL022"),
    ):
        _require_shape(
            issues,
            _valid_fact_list(
                preconditions.get(name),
                nullable_hash=nullable_hash,
            ),
            code,
            f"{name} must be sorted path/hash facts.",
            f"preconditions.{name}",
        )
    candidate = plan.get("candidate_profile")
    _require_shape(
        issues,
        _valid_candidate(candidate),
        "PL023",
        "candidate_profile has an invalid shape.",
        "candidate_profile",
    )
    candidate_path = (
        Path(candidate["path"])
        if isinstance(candidate, Mapping)
        and _is_relative_file_path(candidate.get("path"))
        else None
    )
    return (
        policy["id"] if policy_shape else None,
        candidate_path,
        changed_paths,
        retired_domains,
    )


def _decode_plan_outputs(
    plan: Mapping[str, Any],
    issues: list[ValidationIssue],
) -> None:
    _require_shape(
        issues,
        _valid_changes(plan.get("changes")),
        "PL024",
        "changes must be finite sorted summaries.",
        "changes",
    )
    _require_shape(
        issues,
        _valid_string_list(plan.get("affected_domains")),
        "PL027",
        "affected_domains must be sorted unique strings.",
        "affected_domains",
    )
    actions = plan.get("domain_actions")
    _require_shape(
        issues,
        isinstance(actions, Mapping)
        and all(
            isinstance(key, str)
            and key
            and isinstance(value, str)
            and value in _DOMAIN_ACTIONS
            for key, value in actions.items()
        ),
        "PL028",
        "domain_actions must map registry domains to known actions.",
        "domain_actions",
    )
    _require_shape(
        issues,
        _valid_file_actions(plan.get("file_actions")),
        "PL029",
        "file_actions must have unique safe paths, expected_sha256, update "
        "semantics, snapshots/ metadata, and complete inspected transaction.",
        "file_actions",
    )
    resolutions = plan.get("repair_resolutions")
    _require_shape(
        issues,
        isinstance(resolutions, Mapping)
        and all(
            isinstance(key, str)
            and key
            and isinstance(value, str)
            and value
            for key, value in resolutions.items()
        ),
        "PL035",
        "repair_resolutions must map non-empty strings.",
        "repair_resolutions",
    )
    _require_shape(
        issues,
        type(plan.get("requires_review")) is bool,
        "PL036",
        "requires_review must be boolean.",
        "requires_review",
    )
    review = plan.get("review_binding")
    _require_shape(
        issues,
        isinstance(review, Mapping)
        and (
            not review
            or set(review) == {"candidate_profile_sha256"}
            and _valid_hash(review.get("candidate_profile_sha256"))
        ),
        "PL037",
        "review_binding has an invalid shape.",
        "review_binding",
    )
    phase = plan.get("expected_phase")
    _require_shape(
        issues,
        isinstance(phase, str) and phase in _SAFE_PHASES,
        "PL038",
        "expected_phase is invalid.",
        "expected_phase",
    )
    _require_shape(
        issues,
        _valid_validation(plan.get("validation")),
        "PL039",
        "validation must contain finite issue objects.",
        "validation",
    )
    detail_error = _detail_contract_error(plan)
    _require_shape(
        issues,
        detail_error is None,
        "PL040",
        detail_error or "",
        "detail_references",
    )


def _decode_plan_digest(
    plan: Mapping[str, Any],
    issues: list[ValidationIssue],
) -> None:
    digest = plan.get("plan_sha256")
    _require_shape(
        issues,
        _valid_hash(digest),
        "PL044",
        "plan_sha256 is invalid.",
    )
    if not _valid_hash(digest):
        return
    try:
        expected = canonical_plan_sha256(plan)
    except (TypeError, ValueError) as exc:
        _require_shape(
            issues,
            False,
            "PL045",
            f"Plan is not canonically serializable: {type(exc).__name__}.",
        )
        return
    _require_shape(
        issues,
        digest == expected,
        "PL046",
        "plan_sha256 does not match the canonical payload.",
    )
    plan_id = plan.get("plan_id")
    _require_shape(
        issues,
        isinstance(plan_id, str)
        and bool(_PLAN_ID_PATTERN.fullmatch(plan_id))
        and plan_id == expected[7:23],
        "PL047",
        "plan_id does not match the canonical digest.",
    )


def _decode_plan_document(
    plan: Mapping[str, Any],
) -> tuple[_PlanDocument | None, list[ValidationIssue]]:
    if not isinstance(plan, Mapping):
        return None, [ValidationIssue("PL001", "Plan must be a mapping.")]
    issues: list[ValidationIssue] = []
    project_root, rulers_dir = _decode_plan_identity(plan, issues)
    policy_id, candidate, changed, retired = _decode_plan_inputs(
        plan,
        issues,
    )
    _decode_plan_outputs(plan, issues)
    _decode_plan_digest(plan, issues)
    if (
        issues
        or project_root is None
        or rulers_dir is None
        or policy_id is None
    ):
        return None, issues
    return (
        _PlanDocument(
            payload=plan,
            project_root=project_root,
            rulers_dir=rulers_dir,
            policy_id=policy_id,
            candidate_path=candidate,
            changed_paths=changed,
            retired_domains=retired,
        ),
        issues,
    )
_SEMANTIC_MESSAGES = {
    "template": "Plan does not match the current template version or fingerprint.",
    "operation": "Plan operation conflicts with authoritative project state.",
    "preconditions": (
        "Plan preconditions do not match authoritative project state, "
        "operation input, transaction evidence, named precondition, write_set, "
        "planner write paths, or derived semantics; the plan cannot be "
        "revalidated and Noop must be empty."
    ),
    "affected_domains": (
        "affected_domains do not match authoritative derived semantics or registry."
    ),
    "domain_actions": (
        "domain_actions do not match affected_domains, retired_domains, "
        "registry-derived semantics, or the planner."
    ),
    "file_actions": (
        "file_actions do not match write_set, expected_sha256, update/restore "
        "derived semantics, snapshots/, or the complete inspected transaction; "
        "retire must not physically delete files and Noop must be empty."
    ),
}


def _validate_plan(
    plan: Mapping[str, Any],
    *,
    skill_root: Path,
) -> list[ValidationIssue]:
    document, issues = _decode_plan_document(plan)
    if document is None:
        return issues
    try:
        facts = _capture_planning_facts(
            skill_root=skill_root,
            project_root=document.project_root,
            rulers_dir=document.rulers_dir,
            policy_id=document.policy_id,
            candidate_profile=document.candidate_path,
            changed_paths=document.changed_paths,
            retired_domains=document.retired_domains,
        )
        expected = _assemble_plan(
            facts,
            requested_operation="auto",
            requested_resolutions=plan.get("repair_resolutions", {}),
        )
    except (
        OSError,
        UnicodeDecodeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        return [
            ValidationIssue(
                "PL090",
                "Plan cannot be revalidated against authoritative project state: "
                f"operation input {type(exc).__name__}: {exc}",
            )
        ]

    for field in sorted(_TOP_LEVEL_FIELDS - {"plan_id", "plan_sha256"}):
        if plan.get(field) != expected.get(field):
            issues.append(
                ValidationIssue(
                    "PL091",
                    _SEMANTIC_MESSAGES.get(
                        field,
                        f"{field} does not match derived semantics or "
                        "authoritative project state.",
                    ),
                    field,
                )
            )
    return issues
def validate_plan(
    plan: Mapping[str, Any],
    *,
    skill_root: Path,
) -> list[ValidationIssue]:
    return _validate_plan(plan, skill_root=skill_root)


def _plan_json_bytes(plan: Mapping[str, Any]) -> bytes:
    return (json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _safe_output_path(layout: RulersLayout, output: Path | None, plan_id: str) -> Path:
    if output is None:
        path = layout.rulers_root / ".plans" / plan_id / "plan.json"
    else:
        if output.is_absolute():
            raise ValueError("Plan output must be a project-relative JSON file path.")
        path, _ = _relative_path(layout.project_root, output, label="plan output")
        if path.suffix.casefold() != ".json":
            raise ValueError("Plan output must be a JSON file path inside the project root.")
        try:
            rulers_relative = path.relative_to(layout.rulers_root)
        except ValueError:
            pass
        else:
            if (
                not rulers_relative.parts
                or rulers_relative.parts[0] != ".plans"
                or len(rulers_relative.parts) < 2
            ):
                raise ValueError(
                    "Plan output inside the rulers tree must be under .plans/."
                )
    if path.is_symlink():
        raise ValueError(f"Plan output must not be a symbolic link: {path}")
    return path


@dataclass(frozen=True)
class _CreatedArtifact:
    path: Path


def _ensure_bundle_parent(
    layout: RulersLayout,
    parent: Path,
) -> list[Path]:
    _, relative = _relative_path(
        layout.project_root,
        parent,
        label="plan output parent",
    )
    created: list[Path] = []
    current = layout.project_root
    for component in Path(relative).parts:
        current = current / component
        if _lexists(current):
            if current.is_symlink() or not current.is_dir():
                raise ValueError(
                    f"Plan output parent is not a safe directory: {current}"
                )
            continue
        try:
            current.mkdir()
        except FileExistsError:
            if current.is_symlink() or not current.is_dir():
                raise ValueError(
                    f"Plan output parent was concurrently replaced: {current}"
                )
        else:
            created.append(current)
    _relative_path(
        layout.project_root,
        parent,
        label="plan output parent",
    )
    return created


def _read_existing_artifact(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            f"Plan bundle target must be a regular non-symlink file: {path}"
        )
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(
            f"Plan bundle target cannot be read safely: {path}"
        ) from exc


def _exclusive_create(path: Path, content: bytes) -> bool:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        if _read_existing_artifact(path) == content:
            return False
        raise ValueError(
            f"Refusing to overwrite an existing plan bundle artifact: {path}"
        )
    created = True
    try:
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while creating plan bundle")
            view = view[written:]
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        if created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    else:
        os.close(descriptor)
    _fsync_parent(path.parent)
    return True


def _fsync_parent(parent: Path) -> None:
    try:
        descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _cleanup_bundle_artifacts(
    artifacts: Sequence[_CreatedArtifact],
    directories: Sequence[Path],
) -> None:
    for artifact in reversed(artifacts):
        try:
            artifact.path.unlink()
        except FileNotFoundError:
            pass
    for directory in reversed(directories):
        try:
            directory.rmdir()
        except (FileNotFoundError, OSError):
            pass


def _detail_payloads(
    plan: Mapping[str, Any],
    layout: RulersLayout,
) -> dict[str, bytes]:
    detail_error = _detail_contract_error(plan)
    if detail_error:
        raise ValueError(detail_error)
    references = plan.get("detail_references")
    if references == []:
        return {}
    patch = _profile_patch(plan, layout)
    if patch is None:
        raise ValueError(
            "profile.patch was requested but cannot be generated "
            "from the recorded operation inputs."
    )
    return {"profile.patch": patch}


def _profile_patch(plan: Mapping[str, Any], layout: RulersLayout) -> bytes | None:
    if "profile.patch" not in plan.get("detail_references", ()):
        return None
    candidate = plan.get("candidate_profile")
    reviewed = (plan.get("preconditions") or {}).get("reviewed_profile")
    if not isinstance(candidate, Mapping) or not isinstance(reviewed, Mapping):
        raise ValueError("profile.patch requires candidate and reviewed Profile preconditions.")
    candidate_path, _ = _relative_path(layout.project_root, Path(candidate["path"]), label="candidate profile")
    reviewed_path, _ = _relative_path(layout.project_root, Path(reviewed["path"]), label="reviewed profile")
    for label, path, expected in (
        ("candidate profile", candidate_path, candidate.get("sha256")),
        ("reviewed profile", reviewed_path, reviewed.get("sha256")),
    ):
        if path.is_symlink() or not path.is_file() or file_sha256(path) != expected:
            raise ValueError(f"{label} changed after plan finalization; refusing to write profile.patch.")
    before = reviewed_path.read_text(encoding="utf-8").splitlines(keepends=True)
    after = candidate_path.read_text(encoding="utf-8").splitlines(keepends=True)
    patch = "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile=reviewed["path"],
            tofile=candidate["path"],
        )
    ).encode("utf-8")
    if not patch:
        raise ValueError("Plan references profile.patch but the Profile inputs are identical.")
    return patch


def write_plan_bundle(
    plan: Mapping[str, Any],
    *,
    layout: RulersLayout,
    output: Path | None = None,
) -> Path | None:
    document, issues = _decode_plan_document(plan)
    if document is None:
        raise ValueError(
            "Plan bundle requires a valid plan document: "
            + "; ".join(issue.message for issue in issues)
        )
    if (
        document.project_root != layout.project_root
        or document.rulers_dir != layout.rulers_dir
    ):
        raise ValueError(
            "Plan document does not match the requested project layout."
        )
    if plan.get("operation") == "noop":
        return None
    plan_id = plan.get("plan_id")
    if not isinstance(plan_id, str) or not _PLAN_ID_PATTERN.fullmatch(plan_id):
        raise ValueError("Plan bundle requires a valid plan_id.")
    plan_path = _safe_output_path(layout, output, plan_id)
    plan_content = _plan_json_bytes(plan)
    details = _detail_payloads(plan, layout)
    payloads = {
        **details,
        "plan.json": plan_content,
    }
    created_directories = _ensure_bundle_parent(layout, plan_path.parent)
    created_artifacts: list[_CreatedArtifact] = []
    try:
        unexpected_patch = plan_path.parent / "profile.patch"
        if "profile.patch" not in payloads and _lexists(unexpected_patch):
            raise ValueError(
                "Plan bundle directory contains an unexpected profile.patch: "
                f"{unexpected_patch}"
            )
        for name, content in payloads.items():
            target = plan_path.parent / name
            if _lexists(target) and _read_existing_artifact(target) != content:
                raise ValueError(
                    "Refusing to overwrite an existing plan bundle artifact: "
                    f"{target}"
                )
        for name in (*sorted(details), "plan.json"):
            target = plan_path.parent / name
            if _exclusive_create(target, payloads[name]):
                created_artifacts.append(_CreatedArtifact(target))
    except BaseException:
        _cleanup_bundle_artifacts(created_artifacts, created_directories)
        raise
    return plan_path


def load_plan(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Plan path must be a regular non-symlink file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Plan file is unreadable or invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Plan file must contain a JSON object: {path}")
    digest = payload.get("plan_sha256")
    expected = canonical_plan_sha256(payload)
    if digest != expected or payload.get("plan_id") != expected[7:23]:
        raise ValueError(f"Plan file hash or ID does not match its payload: {path}")
    try:
        layout = resolve_layout(Path(payload["project_root"]), payload["rulers_dir"])
        loaded_path, _ = _relative_path(layout.project_root, path, label="plan path")
    except (KeyError, TypeError, ValueError, UnsafeRulersPathError) as exc:
        raise ValueError(f"Plan path or layout is unsafe: {path}") from exc
    candidate = payload.get("candidate_profile")
    if candidate is not None:
        if not isinstance(candidate, Mapping):
            raise ValueError("candidate Profile operation input has an invalid shape.")
        _current_input_fact(
            layout.project_root,
            {"path": candidate.get("path"), "sha256": candidate.get("sha256")},
            label="candidate Profile operation input",
        )
    preconditions = payload.get("preconditions")
    operation_inputs = (
        preconditions.get("operation_inputs")
        if isinstance(preconditions, Mapping)
        else None
    )
    changed_inputs = (
        operation_inputs.get("changed_paths")
        if isinstance(operation_inputs, Mapping)
        else None
    )
    if not isinstance(changed_inputs, list):
        raise ValueError("operation input changed paths have an invalid shape.")
    for changed_input in changed_inputs:
        if not isinstance(changed_input, Mapping):
            raise ValueError("operation input changed path has an invalid shape.")
        _current_input_fact(
            layout.project_root,
            changed_input,
            label="operation input changed path",
        )
    expected_details = _detail_payloads(payload, layout)
    for name, expected_content in expected_details.items():
        detail_path = loaded_path.parent / name
        if detail_path.is_symlink() or not detail_path.is_file():
            raise ValueError(f"Plan detail is missing or unsafe: {name}")
        if detail_path.read_bytes() != expected_content:
            raise ValueError(
                f"{name} does not match the bound operation inputs."
            )
    return payload


def plan_summary(
    plan: Mapping[str, Any],
    plan_path: Path | None,
) -> dict[str, Any]:
    safe_plan_path: str | None = None
    if plan_path is not None:
        project_root = plan.get("project_root")
        if isinstance(project_root, str):
            try:
                candidate, relative = _relative_path(Path(project_root), plan_path, label="plan path")
            except ValueError:
                pass
            else:
                if not candidate.is_symlink():
                    safe_plan_path = relative
    return {
        "operation": plan.get("operation"),
        "plan_id": plan.get("plan_id"),
        "expected_phase": plan.get("expected_phase"),
        "affected_domains": list(plan.get("affected_domains") or ()),
        "domain_actions": dict(plan.get("domain_actions") or {}),
        "requires_review": plan.get("requires_review"),
        "plan_path": safe_plan_path,
        "detail_references": list(plan.get("detail_references") or ()),
    }
