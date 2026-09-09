"""Unified Apply orchestrator for ai-rulers-init schema 3 lifecycle.

This module implements the single Apply pipeline:
  validate plan -> check already applied -> verify preconditions ->
  verify review -> build write set -> execute within transaction ->
  validate after apply -> update State
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .issues import ValidationIssue
from .paths import RulersLayout, resolve_layout
from .plans import load_plan, plan_summary
from .state import (
    SCHEMA_VERSION,
    file_sha256,
    read_state,
    transition_state,
)
from .transactions import FileTransaction, file_transaction, maintenance_lock, write_state_atomic


class ApplyError(ValueError):
    """Raised when Apply cannot proceed."""


class RepairError(ApplyError):
    """Raised when a repair resolution cannot be applied."""


REPAIR_ACTIONS = frozenset({"restore-managed", "adopt-current", "manual-merge"})


def validate_repair_resolution(
    path: str,
    action: str,
    *,
    state: Mapping[str, Any] | None,
    project_root: Path,
) -> None:
    """Validate a single repair resolution is applicable."""
    if action not in REPAIR_ACTIONS:
        raise RepairError(
            f"Unknown repair action '{action}' for {path}. "
            f"Valid actions: {', '.join(sorted(REPAIR_ACTIONS))}."
        )
    if action == "restore-managed":
        # Only allowed if template_id can deterministically rebuild
        managed = (state or {}).get("managed_files") or {}
        metadata = managed.get(path)
        if not isinstance(metadata, Mapping):
            raise RepairError(
                f"Cannot restore-managed '{path}': not in managed inventory."
            )
        if metadata.get("ownership") == "project-generated":
            raise RepairError(
                f"Cannot restore-managed '{path}': project-generated files "
                "require adopt-current or manual-merge."
            )
    elif action == "manual-merge":
        # manual-merge does not write; user must replan after merging
        pass


def apply_repair_resolution(
    path: str,
    action: str,
    *,
    state: dict[str, Any],
    project_root: Path,
    layout: Any,
) -> dict[str, Any]:
    """Apply a repair resolution and return updated state."""
    from .state import file_sha256

    if action == "adopt-current":
        file_path = project_root / path
        if not file_path.is_file():
            raise RepairError(f"Cannot adopt-current '{path}': file does not exist.")
        managed = state.setdefault("managed_files", {})
        metadata = managed.setdefault(path, {})
        metadata["rendered_sha256"] = file_sha256(file_path)
        if metadata.get("ownership") == "managed":
            metadata["ownership"] = "collaborative"
    elif action == "restore-managed":
        # Restoration is handled by the transaction/apply pipeline
        pass
    elif action == "manual-merge":
        # No write; user must replan
        pass
    return state


def validate_plan_for_apply(
    plan: Mapping[str, Any], *, skill_root: Path, project_root: Path
) -> None:
    """Validate that the plan is structurally valid and applicable."""
    plan_project = plan.get("project_root")
    if plan_project != str(project_root):
        raise ApplyError(
            f"Plan project_root '{plan_project}' does not match "
            f"requested project_root '{project_root}'."
        )
    operation = plan.get("operation")
    if operation == "noop":
        raise ApplyError("Cannot apply a noop plan.")


def is_already_applied(
    state: Mapping[str, Any] | None, plan: Mapping[str, Any]
) -> bool:
    """Check if this exact plan has already been applied."""
    if state is None:
        return False
    last_op = state.get("last_operation")
    if not isinstance(last_op, Mapping):
        return False
    if last_op.get("status") not in {"complete", "completed"}:
        return False
    if last_op.get("plan_id") != plan.get("plan_id"):
        return False
    if last_op.get("plan_sha256") != plan.get("plan_sha256"):
        return False
    return True


def verify_preconditions(
    plan: Mapping[str, Any], *, project_root: Path
) -> None:
    """Verify that plan preconditions still hold (no stale inputs)."""
    preconditions = plan.get("preconditions")
    if not isinstance(preconditions, Mapping):
        raise ApplyError("Plan is missing preconditions.")
    # Check read_set hashes still match
    read_set = (preconditions.get("read_set") or []) + (preconditions.get("write_set") or [])
    for entry in read_set:
        if not isinstance(entry, Mapping):
            continue
        path_str = entry.get("path")
        expected_hash = entry.get("sha256")
        if not path_str:
            raise ApplyError("Missing precondition path")
        from .paths import resolve_safe_child
        file_path = resolve_safe_child(project_root, path_str)
        if expected_hash is None:
            if file_path.exists():
                raise ApplyError(f"VR041 unexpected file appeared: {path_str}")
            continue
        if not file_path.is_file():
            raise ApplyError(
                f"Precondition file missing: {path_str}"
            )
        actual = file_sha256(file_path)
        if actual != expected_hash:
            raise ApplyError(
                f"Precondition file changed since plan creation: {path_str}"
            )


def verify_review(
    plan: Mapping[str, Any],
    *,
    reviewed_by: str | None,
    evidence: str | None,
) -> None:
    """Verify review requirements for the plan operation."""
    operation = plan.get("operation")
    requires_review = plan.get("requires_review", False)
    if operation == "fresh":
        return  # fresh does not require review
    if requires_review or operation in ("reconcile", "upgrade", "repair"):
        if not reviewed_by:
            raise ApplyError(
                f"Operation '{operation}' requires --reviewed-by."
            )
        if not evidence:
            raise ApplyError(
                f"Operation '{operation}' requires --evidence."
            )


def apply_plan_unified(
    plan_path: Path, *, skill_root: Path, project_root: Path,
    reviewed_by: str | None = None, evidence: str | None = None,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    import copy
    from .plans import canonical_plan_sha256, validate_plan, _tree_fingerprint
    from .runtime_files import runtime_files, retired_runtime_files
    from .mutations import mutation
    from .state import create_initial_state, state_json, text_sha256
    from .policies import load_policy
    from .validation import validate_project
    from .transactions import ReplaceAction, DeleteAction, restore_transaction
    from .paths import resolve_safe_child

    project_root = project_root.resolve()
    if plan_path.is_symlink():
        raise ApplyError("Plan must not be a symlink")
    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    if raw.get("plan_sha256") != canonical_plan_sha256(raw) or raw.get("plan_id") != raw["plan_sha256"][7:23]:
        raise ApplyError("Plan hash or ID mismatch")
    layout = resolve_layout(project_root, raw["rulers_dir"])
    if raw.get("project_root") != str(project_root):
        raise ApplyError("Plan project_root does not match requested project")
    state_path = layout.rulers_root / "RULERS_STATE.json"
    current = read_state(state_path) if state_path.is_file() else None
    if is_already_applied(current, raw):
        for path, expected in current["last_operation"].get("result_hashes", {}).items():
            target = resolve_safe_child(project_root, path)
            if not target.is_file() or file_sha256(target) != expected:
                raise ApplyError("VR040 applied output changed; create a repair plan")
        return {"already_applied": True, "operation": raw["operation"], "changed_files": [], "phase": current["phase"]}
    plan = load_plan(plan_path)
    issues = validate_plan(plan, skill_root=skill_root)
    if issues:
        raise ApplyError("Plan validation failed: " + "; ".join(i.message for i in issues))
    if plan["operation"] == "noop":
        return {"operation": "noop", "changed_files": [], "phase": current["phase"]}
    verify_review(plan, reviewed_by=reviewed_by, evidence=evidence)
    verify_preconditions(plan, project_root=project_root)
    transaction_evidence = plan["preconditions"].get("transaction_evidence")
    if transaction_evidence:
        from .transactions import inspect_incomplete_transaction
        inspected = inspect_incomplete_transaction(layout)
        if inspected is None:
            raise ApplyError("Repair transaction evidence disappeared; replan")
        changed = restore_transaction(layout=layout, transaction_id=inspected.transaction_id,
                                      expected_lock_sha256=inspected.lock_sha256, expected_lock_nonce=inspected.lock_nonce)
        return {"operation": "repair", "changed_files": list(changed), "next_action": "replan"}

    operation = plan["operation"]
    if operation == "reconcile" and not plan["changes"] and all(action == "keep" for action in plan["domain_actions"].values()) and (not plan.get("candidate_profile") or plan["candidate_profile"]["sha256"] == (current.get("profile") or {}).get("reviewed_sha256")):
        return {"operation": "noop", "changed_files": [], "phase": current["phase"]}
    timestamp = reviewed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    policy = plan["preconditions"]["policy"]
    state = copy.deepcopy(current) if current else create_initial_state(
        rulers_dir=layout.rulers_dir, policy_id=policy["id"],
        detected_domains=[d for d in plan["domain_actions"] if d != "core"],
    )
    writes: dict[str, bytes] = {}
    removals: set[str] = set()
    inventory = state.setdefault("managed_files", {})
    profile_relative = f"{layout.rulers_dir}/PROJECT_PROFILE.md"
    if operation in {"fresh", "resume", "upgrade"}:
        writes = runtime_files(skill_root=skill_root, layout=layout, policy_id=policy["id"], state=state)
        for path in writes:
            if path in {"AGENTS.md", "CLAUDE.md", "CHANGELOG.md"}:
                continue
            existing = project_root / path
            metadata = inventory.get(path)
            if existing.exists() and (not metadata or metadata.get("ownership") != "managed"):
                raise ApplyError(f"VR041 unmanaged file conflict: {path}")
        removals = retired_runtime_files(layout=layout, policy_id=policy["id"], state=state)
        for path in removals:
            inventory.pop(path, None)
        state["schema_version"] = SCHEMA_VERSION
        state.pop("template_version", None)
        state["template"] = plan["template"]
        state["policy"] = policy
        if operation == "fresh":
            candidate = plan.get("candidate_profile")
            if candidate:
                writes[profile_relative] = resolve_safe_child(project_root, candidate["path"]).read_bytes()
            state["phase"] = "profile_draft"
        elif operation == "upgrade":
            profile = state["profile"]
            old_hash = profile.get("content_sha256")
            bound_profile = plan["preconditions"].get("reviewed_profile") or {}
            review = profile.get("review") or {}
            if not profile.get("reviewed_sha256") and old_hash == bound_profile.get("sha256") and old_hash and all(review.get(key) for key in ("reviewed_by", "reviewed_at", "evidence")):
                profile["reviewed_sha256"] = old_hash
            if not profile.get("reviewed_sha256"):
                # Old producer schemas cannot prove the new Profile contract.
                profile["status"] = "draft"
                state["phase"] = "profile_draft"
                for domain in state["domains"].values():
                    domain.update(level=0, review_status="draft", level3_ready=False)
            else:
                state["phase"] = plan["expected_phase"]
    elif operation == "reconcile":
        candidate = plan.get("candidate_profile")
        if candidate:
            content = resolve_safe_child(project_root, candidate["path"]).read_bytes()
            if file_sha256(resolve_safe_child(project_root, candidate["path"])) != candidate["sha256"]:
                raise ApplyError("Candidate profile changed")
            writes[profile_relative] = content
            state["profile"] = {"status": "reviewed", "reviewed_sha256": candidate["sha256"],
                "review": {"reviewed_by": reviewed_by, "reviewed_at": timestamp, "evidence": evidence}}
            state["domains"]["core"].update(level=1, review_status="reviewed", review=state["profile"]["review"])
        for domain, action in plan["domain_actions"].items():
            if action == "keep":
                continue
            value = state["domains"].setdefault(domain, {"target_dir": domain, "required_files": ["INDEX.md"]})
            if domain == "core":
                continue
            value.update(level=0, review_status="draft", level3_ready=False)
            if action == "retire":
                value["retired"] = True
            value["review"] = {"reviewed_by": None, "reviewed_at": None, "evidence": None}
    elif operation == "repair":
        resolutions = plan.get("repair_resolutions", {})
        if not resolutions:
            raise ApplyError("Repair requires an explicit managed-file resolution")
        rendered = runtime_files(skill_root=skill_root, layout=layout, policy_id=policy["id"])
        for path, action in resolutions.items():
            validate_repair_resolution(path, action, state=state, project_root=project_root)
            if action in {"manual-review", "manual-merge"}:
                raise ApplyError("Complete manual merge and replan with adopt-current")
            target = resolve_safe_child(project_root, path)
            if action == "restore-managed":
                if path not in rendered:
                    raise ApplyError(f"No deterministic source for {path}; use rules maintenance")
                writes[path] = rendered[path]
            else:
                if not target.is_file():
                    raise ApplyError(f"Cannot adopt missing {path}")
                inventory[path]["rendered_sha256"] = file_sha256(target)
                # Preserve drift checks, but record project provenance for upgrades.
                inventory[path]["project_owned"] = True
                from .validation import _scope_for_managed_path
                from .domains import load_domain_registry, expand_reverse_dependencies
                scope = _scope_for_managed_path(path, state)
                if scope not in {None, "core", "entry", "profile"}:
                    for domain in expand_reverse_dependencies({scope}, load_domain_registry(skill_root)):
                        if domain in state["domains"]:
                            state["domains"][domain].update(level=0, review_status="draft", level3_ready=False)
            if path == profile_relative:
                state["profile"]["status"] = "draft"
                state["profile"].pop("reviewed_sha256", None)
                for value in state["domains"].values():
                    value.update(level=0, review_status="draft", level3_ready=False)
        state["phase"] = "runtime_ready" if state["profile"]["status"] == "reviewed" else "profile_draft"

    for path, content in writes.items():
        if path in {"AGENTS.md", "CLAUDE.md", "CHANGELOG.md"}:
            continue
        inventory[path] = {**inventory.get(path, {}), "template_id": path.removeprefix(layout.rulers_dir + "/"),
            "source_sha256": text_sha256(content.decode("utf-8")), "rendered_sha256": text_sha256(content.decode("utf-8")),
            "ownership": "collaborative" if path == profile_relative else "managed"}
    profile_path = project_root / profile_relative
    if profile_relative not in inventory and profile_path.is_file():
        inventory[profile_relative] = {"template_id": "PROJECT_PROFILE.md", "ownership": "collaborative",
            "source_sha256": file_sha256(profile_path), "rendered_sha256": file_sha256(profile_path)}
    state["last_operation"] = {"kind": operation, "operation": operation, "status": "complete",
        "plan_id": plan["plan_id"], "plan_sha256": plan["plan_sha256"],
        "reviewed_by": reviewed_by, "reviewed_at": timestamp, "evidence": evidence,
        "result_hashes": {path: text_sha256(content.decode("utf-8")) for path, content in writes.items()}}
    state_relative = f"{layout.rulers_dir}/RULERS_STATE.json"
    writes[state_relative] = state_json(state).encode("utf-8")
    allowed = {item["path"] for item in plan["preconditions"]["write_set"]}
    if not (set(writes) | removals).issubset(allowed):
        raise ApplyError("Execution writes are not covered by the reviewed plan")
    with mutation(layout, transaction_id=plan["plan_id"]) as transaction:
        verify_preconditions(plan, project_root=project_root)
        if _tree_fingerprint(skill_root) != plan["template"]["fingerprint"]:
            raise ApplyError("Templates changed; replan")
        changed = transaction.apply([ReplaceAction(path, content) for path, content in sorted(writes.items())] + [DeleteAction(path) for path in sorted(removals)])
        errors = [i for i in validate_project(mode="candidate", project_root=project_root, rulers_dir=layout.rulers_dir) if i.severity == "error"]
        if errors:
            raise ApplyError("Post-apply validation failed: " + "; ".join(f"{i.code}: {i.message}" for i in errors))
    return {"operation": operation, "phase": state["phase"], "changed_files": list(changed), "already_applied": False}
