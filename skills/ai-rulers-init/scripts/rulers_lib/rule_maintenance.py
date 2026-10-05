"""One reviewed domain plan, with separately recoverable adoption and activation."""
from __future__ import annotations

import copy
import difflib
from datetime import datetime, timezone
from pathlib import Path

from .domains import (load_domain_registry, expand_reverse_dependencies, effective_domain_configs,
                      effective_dependency_configs, nested_domain_dirs)
from .domain_lifecycle import prepare_domain_activation
from .module_contracts import checked_path, read_json, identity, file_identity
from .paths import resolve_layout
from .plans import _tree_fingerprint
from .state import read_state, state_json, file_sha256
from .mutations import mutation, CURRENT_ID
from .transactions import (ReplaceAction, DeleteAction, inspect_incomplete_transaction,
                           restore_transaction)
from .validation import validate_rule_metadata_text, inspect_project, scoped_validation_issues


def _files(root: Path, *, excluded_dirs=()) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Rule directory must be a regular directory")
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(Path(excluded) == relative or Path(excluded) in relative.parents for excluded in excluded_dirs):
            continue
        if path.is_symlink():
            raise ValueError("Rule trees must not contain symbolic links")
        if path.is_file():
            if path.suffix != ".md":
                raise ValueError("Rule candidate trees contain Markdown only")
            result[relative.as_posix()] = file_sha256(path)
    return result


def _digest(plan):
    return identity({key: value for key, value in plan.items() if key != "sha256"})


def _state_identity(state):
    # Execution cannot bind itself; diagnostic updates are not approval inputs.
    return identity({key: value for key, value in state.items()
                     if key not in {"maintenance_execution", "last_operation"}})


def _skill_identity(skill_root):
    return identity({"engine": _tree_fingerprint(skill_root),
                     "entry": file_identity(skill_root / "SKILL.md"),
                     "maintenance": file_identity(skill_root / "references/maintenance.md")})


def _contracts(configs, declared):
    return {name: {"target_dir": config.get("target_dir", name),
                   "required_files": sorted(config.get("required_files", config.get("templates", []))),
                   "requires_active": sorted(config["requires_active"]),
                   "declared_requires_active": list(declared[name]["requires_active"])}
            for name, config in sorted(configs.items())}


def _project_state(state, plan):
    result = copy.deepcopy(state)
    if plan["preserve_review"]:
        return result
    domain = plan["domain"]
    prefix = f"{plan['rulers_dir']}/{plan['target_dir']}/"
    inventory = result["managed_files"]
    for name in plan["deleted"]:
        inventory.pop(prefix + name, None)
    for name, digest in plan["after"].items():
        inventory[prefix + name] = {"ownership": "managed", "project_owned": True,
                                   "template_id": f"generated/{domain}/{name}",
                                   "source_sha256": digest, "rendered_sha256": digest}
    value = result["domains"].setdefault(domain, {})
    value.update(target_dir=plan["target_dir"], required_files=sorted(plan["after"]),
                 requires_active=list(plan["declared_requires_active"]), generated=True,
                 detected=True, retired=False, level=0, review_status="draft", level3_ready=False,
                 removed_files=sorted((set(value.get("removed_files", [])) | set(plan["deleted"])) - set(plan["after"])),
                 review={"reviewed_by": None, "reviewed_at": None, "evidence": None})
    for dependent in plan["affected_domains"]:
        if dependent != domain and dependent in result["domains"]:
            result["domains"][dependent].update(level=0, review_status="draft", level3_ready=False,
                review={"reviewed_by": None, "reviewed_at": None, "evidence": None})
    if result["phase"] == "profile_reviewed":
        result["phase"] = "rules_candidate"
    return result


def plan_rules_change(*, skill_root: Path, project_root: Path, rulers_dir: str,
                      domain: str, candidate_dir: str, reason: str,
                      activate_on_apply: bool = False, readiness_source: str | None = None) -> dict:
    if not reason.strip() or type(activate_on_apply) is not bool:
        raise ValueError("Rule maintenance requires a reason and explicit activation choice")
    if readiness_source is not None and not activate_on_apply:
        raise ValueError("Readiness source requires --activate-on-apply")
    layout = resolve_layout(project_root, rulers_dir)
    registry = load_domain_registry(skill_root)
    if domain not in registry or domain == "core":
        raise ValueError("Choose a registered project domain; core is maintained by template upgrade")
    state_path = checked_path(layout.rulers_root, "RULERS_STATE.json", required=True)
    state = read_state(state_path)
    inspection = inspect_project(project_root=layout.project_root, rulers_dir=layout.rulers_dir)
    if inspection.global_blocked or not inspection.profile_valid or state["profile"]["status"] != "reviewed":
        raise ValueError("Review or repair project facts and global rules before domain maintenance")
    declared = effective_domain_configs(registry, state)
    config = declared[domain]
    candidate = checked_path(layout.project_root, candidate_dir)
    if candidate == layout.rulers_root or layout.rulers_root in candidate.parents:
        raise ValueError("Stage candidates outside the installed rulers directory")
    target = checked_path(layout.rulers_root, config["target_dir"])
    excluded_dirs = nested_domain_dirs(domain, declared)
    for excluded in excluded_dirs:
        copied = candidate / excluded
        if copied.exists() or copied.is_symlink():
            installed = target / excluded
            if _files(copied) != (_files(installed) if installed.exists() else {}):
                raise ValueError(f"Candidate modifies another domain subtree: {excluded}; maintain it separately")
    desired = _files(candidate, excluded_dirs=excluded_dirs)
    if "INDEX.md" not in desired:
        raise ValueError("Domain candidate needs INDEX.md")
    texts = {}
    for name in desired:
        text = (candidate / name).read_text(encoding="utf-8")
        if "AI_FILL" in text or "{{RULERS_DIR}}" in text or validate_rule_metadata_text(text, name):
            raise ValueError(f"Incomplete rule candidate: {name}")
        texts[f"{layout.rulers_dir}/{config['target_dir']}/{name}"] = text
    old = _files(target, excluded_dirs=excluded_dirs) if target.exists() else {}
    result = {
        "plan_version": 2, "operation": "rules-maintenance", "project_root": str(layout.project_root),
        "rulers_dir": layout.rulers_dir, "domain": domain, "target_dir": config["target_dir"],
        "candidate_dir": candidate.relative_to(layout.project_root).as_posix(),
        "excluded_dirs": list(excluded_dirs), "reason": reason,
        "state_sha256": file_sha256(state_path), "state_before": copy.deepcopy(state),
        "skill_sha256": _skill_identity(skill_root),
        "before": old, "after": desired,
        "added": sorted(desired.keys() - old.keys()), "deleted": sorted(old.keys() - desired.keys()),
        "modified": sorted(name for name in old.keys() & desired.keys() if old[name] != desired[name]),
        "activate_on_apply": activate_on_apply, "activation_scope": [domain] if activate_on_apply else [],
        "declared_requires_active": list(config["requires_active"]), "affected_domains": [domain],
        "preserve_review": False, "readiness_input": None, "supersedes": None,
    }
    changed = bool(result["added"] or result["deleted"] or result["modified"])
    result["preserve_review"] = bool(not changed and activate_on_apply and
        state.get("domains", {}).get(domain, {}).get("level", 0) >= 2 and
        state["domains"][domain].get("review_status") == "reviewed" and domain not in inspection.invalid_domains)
    errors = []
    before_configs = effective_dependency_configs(registry, state, layout, errors=errors)
    projected = _project_state(state, result)
    after_errors = []
    after_configs = effective_dependency_configs(registry, projected, layout, errors=after_errors, rule_text_overrides=texts)
    if changed:
        result["affected_domains"] = sorted(expand_reverse_dependencies({domain}, before_configs)
                                             | expand_reverse_dependencies({domain}, after_configs))
        projected = _project_state(state, result)
    result["dependencies_before"] = _contracts(before_configs, declared)
    result["dependencies_after"] = _contracts(after_configs, effective_domain_configs(registry, projected))
    if readiness_source is not None:
        from .readiness import compile_readiness
        source = checked_path(layout.project_root, readiness_source, required=True)
        source_hash = file_sha256(source)
        declaration = compile_readiness(layout, projected, domain, read_json(source),
            candidate_hashes={f"{layout.rulers_dir}/{config['target_dir']}/{name}": digest for name, digest in desired.items()},
            candidate_texts=texts)
        if file_sha256(source) != source_hash:
            raise ValueError("Readiness source changed during planning")
        result["readiness_input"] = {"path": source.relative_to(layout.project_root).as_posix(),
                                     "sha256": source_hash, "declaration": declaration}
    pending = state.get("maintenance_execution")
    if isinstance(pending, dict) and pending.get("phase") == "activation_pending":
        result["supersedes"] = {key: pending[key] for key in ("plan_sha256", "domain", "activation_scope", "phase")}
        result["supersedes"].update(applied_files=list(pending["applied_files"]),
            output_sha256=pending["output_sha256"], remaining_draft_domains=sorted(
                name for name in pending.get("affected_domains", [pending["domain"]])
                if state.get("domains", {}).get(name, {}).get("level", 0) < 2
                or state["domains"][name].get("review_status") != "reviewed"))
        result["supersedes"]["impact"] = "替换旧待激活计划的恢复依据；已批准采纳内容保留，不自动激活或回滚旧范围"
    result["patch"] = "".join(
        "".join(difflib.unified_diff(
            (target / name).read_text(encoding="utf-8").splitlines(keepends=True) if name in old else [],
            (candidate / name).read_text(encoding="utf-8").splitlines(keepends=True) if name in desired else [],
            fromfile=f"{config['target_dir']}/{name}", tofile=f"candidate/{name}"))
        for name in sorted(set(result["added"] + result["deleted"] + result["modified"])))
    result["sha256"] = _digest(result)
    return result


def _static_inputs(layout, plan, skill_root):
    if _skill_identity(skill_root) != plan["skill_sha256"]:
        raise ValueError("Skill contract changed; replan")
    candidate = checked_path(layout.project_root, plan["candidate_dir"])
    if _files(candidate, excluded_dirs=plan["excluded_dirs"]) != plan["after"]:
        raise ValueError("Candidate changed; replan")
    source = plan["readiness_input"]
    if source is not None and file_identity(checked_path(layout.project_root, source["path"], required=True)) != source["sha256"]:
        raise ValueError("Readiness source changed; replan")


def _execution_matches(state, plan, reviewed_by, evidence):
    execution = state.get("maintenance_execution")
    if not isinstance(execution, dict) or execution.get("plan_sha256") != plan["sha256"]:
        raise ValueError("Maintenance recovery does not belong to this approved plan")
    if execution.get("domain") != plan["domain"] or execution.get("activation_scope") != plan["activation_scope"]:
        raise ValueError("Maintenance activation scope changed; replan")
    review = execution.get("review", {})
    if (not isinstance(review, dict) or set(review) != {"reviewed_by", "reviewed_at", "evidence"}
            or review.get("reviewed_by") != reviewed_by.strip() or review.get("evidence") != evidence.strip()):
        raise ValueError("Maintenance continuation requires the original approval")
    if (not isinstance(review.get("reviewed_at"), str) or not review["reviewed_at"].strip()
            or execution.get("review_sha256") != identity(review)):
        raise ValueError("Maintenance approval record changed")
    if execution.get("output_sha256") != _state_identity(state):
        raise ValueError("Maintenance State outputs changed; replan")
    expected_files = sorted({f"{plan['rulers_dir']}/{plan['target_dir']}/{name}"
                             for name in plan["added"] + plan["modified"] + plan["deleted"]}
                            | {f"{plan['rulers_dir']}/RULERS_STATE.json"})
    if execution.get("affected_domains") != plan["affected_domains"] or execution.get("applied_files") != expected_files:
        raise ValueError("Maintenance recorded outputs or affected scope changed")
    return execution


def _approved_output(layout, state, plan, skill_root, execution):
    expected = _project_state(plan["state_before"], plan)
    if execution["phase"] == "complete" and plan["activate_on_apply"]:
        expected["maintenance_execution"] = copy.deepcopy(execution)
        expected = _complete_state(layout, expected, plan, skill_root)
    elif execution["phase"] != ("activation_pending" if plan["activate_on_apply"] else "complete"):
        raise ValueError("Maintenance phase exceeds its approved execution")
    if _state_identity(state) != _state_identity(expected):
        raise ValueError("Maintenance State differs from the approved phase output; replan")


def _check_outputs(layout, state, plan, skill_root, reviewed_by, evidence):
    _static_inputs(layout, plan, skill_root)
    execution = _execution_matches(state, plan, reviewed_by, evidence)
    _approved_output(layout, state, plan, skill_root, execution)
    target = checked_path(layout.rulers_root, plan["target_dir"])
    if _files(target, excluded_dirs=plan["excluded_dirs"]) != plan["after"]:
        raise ValueError("Adopted maintenance outputs changed; replan")
    registry = load_domain_registry(skill_root)
    errors = []
    configs = effective_dependency_configs(registry, state, layout, errors=errors)
    if _contracts(configs, effective_domain_configs(registry, state)) != plan["dependencies_after"]:
        raise ValueError("Effective maintenance dependencies changed; replan")
    inspection = inspect_project(project_root=layout.project_root, rulers_dir=layout.rulers_dir)
    blockers = scoped_validation_issues(inspection, [plan["domain"]],
        require_active_dependencies=bool(plan["activate_on_apply"] and execution["phase"] == "complete"))
    if blockers:
        raise ValueError("Maintenance scope validation failed: " + "; ".join(f"{i.code} {i.message}" for i in blockers))
    if plan["readiness_input"] is not None:
        from .readiness import compile_readiness
        source = plan["readiness_input"]
        if compile_readiness(layout, state, plan["domain"], read_json(checked_path(layout.project_root, source["path"], required=True))) != source["declaration"]:
            raise ValueError("Readiness approval inputs changed; replan")
    return execution


def _complete_state(layout, state, plan, skill_root):
    result = copy.deepcopy(state)
    execution = result["maintenance_execution"]
    review = execution["review"]
    readiness = plan["readiness_input"]
    activated = prepare_domain_activation(skill_root=skill_root, layout=layout, state=result,
        domain=plan["domain"], reviewed_by=review["reviewed_by"], evidence=review["evidence"],
        reviewed_at=review["reviewed_at"], readiness=readiness["declaration"] if readiness else None,
        preserve_review=plan["preserve_review"], approval_plan_sha256=plan["sha256"])
    execution.update(phase="complete", output_sha256=_state_identity(result), activation_result=activated)
    return result


def _transaction_ids(plan):
    prefix = plan["sha256"].removeprefix("sha256:")[:16]
    return prefix + "-rules", prefix + "-activate"


def _recover_owned(layout, plan, skill_root, reviewed_by, evidence):
    interrupted = inspect_incomplete_transaction(layout)
    if interrupted is None:
        return
    rule_id, activate_id = _transaction_ids(plan)
    if interrupted.requires_replan or interrupted.transaction_id not in {rule_id, activate_id}:
        raise ValueError("Unrelated or incomplete transaction requires explicit lifecycle recovery")
    _static_inputs(layout, plan, skill_root)
    state_relative = f"{layout.rulers_dir}/RULERS_STATE.json"
    state_path = checked_path(layout.project_root, state_relative, required=True)
    state_action = next((action for action in interrupted.actions if action.path == state_relative), None)
    original = None
    if state_action is not None:
        if not state_action.original_existed or state_action.snapshot_ref is None:
            raise ValueError("Maintenance recovery requires its original State snapshot")
        snapshot = checked_path(layout.transaction_root(interrupted.transaction_id), state_action.snapshot_ref, required=True)
        if file_sha256(snapshot) != state_action.snapshot_sha256:
            raise ValueError("Maintenance recovery snapshot changed")
        original = read_state(snapshot)
    current = read_state(state_path)
    if interrupted.transaction_id == activate_id:
        if state_action is None or len(interrupted.actions) != 1:
            raise ValueError("Activation recovery journal crosses the approved State write")
        token = CURRENT_ID.set(activate_id)
        try:
            _check_outputs(layout, original, plan, skill_root, reviewed_by, evidence)
            expected = _complete_state(layout, original, plan, skill_root)
        finally:
            CURRENT_ID.reset(token)
        if _state_identity(current) not in {_state_identity(original), _state_identity(expected)}:
            raise ValueError("Activation output changed outside its journal; replan")
        record = current.get("maintenance_execution", {})
        if record.get("phase") not in {"activation_pending", "complete"}:
            raise ValueError("Activation recovery phase changed")
        _execution_matches(current, plan, reviewed_by, evidence)
    else:
        if state_action is not None and (state_action.original_sha256 != plan["state_sha256"]
                or original != plan["state_before"]):
            raise ValueError("Adoption recovery State does not match the approved input")
        known = {f"{layout.rulers_dir}/{plan['target_dir']}/{name}": plan["after"].get(name)
                 for name in plan["added"] + plan["modified"] + plan["deleted"]}
        for action in interrupted.actions:
            if action.path == state_relative:
                continue
            prefix = f"{layout.rulers_dir}/{plan['target_dir']}/"
            original_hash = plan["before"].get(action.path.removeprefix(prefix))
            if (action.path not in known or action.original_sha256 != original_hash
                    or action.original_existed != (original_hash is not None)
                    or file_identity(checked_path(layout.project_root, action.path)) not in {original_hash, known[action.path]}):
                raise ValueError("Adoption journal or output exceeds the approved write set")
        if file_sha256(state_path) != plan["state_sha256"]:
            if original is None or _state_identity(current) != _state_identity(_project_state(plan["state_before"], plan)):
                raise ValueError("Adoption State changed outside its journal; replan")
            _execution_matches(current, plan, reviewed_by, evidence)
    restore_transaction(layout=layout, transaction_id=interrupted.transaction_id,
                        expected_lock_sha256=interrupted.lock_sha256, expected_lock_nonce=interrupted.lock_nonce)


def apply_rules_change(*, plan: dict, skill_root: Path, reviewed_by: str, evidence: str) -> dict:
    if not reviewed_by.strip() or not evidence.strip():
        raise ValueError("Rule changes require reviewer and evidence")
    if plan.get("sha256") != _digest(plan) or plan.get("plan_version") != 2:
        raise ValueError("Rule maintenance plan digest or protocol mismatch; replan")
    domain = plan["domain"]
    if plan["activation_scope"] != ([domain] if plan["activate_on_apply"] else []):
        raise ValueError("Rule maintenance activation scope must be the target domain only")
    layout = resolve_layout(Path(plan["project_root"]), plan["rulers_dir"])
    _recover_owned(layout, plan, skill_root, reviewed_by, evidence)
    state_relative = f"{layout.rulers_dir}/RULERS_STATE.json"
    rule_id, activate_id = _transaction_ids(plan)
    with mutation(layout, transaction_id=rule_id) as transaction:
        state = read_state(layout.rulers_root / "RULERS_STATE.json")
        execution = state.get("maintenance_execution", {})
        if execution.get("plan_sha256") == plan["sha256"]:
            execution = _check_outputs(layout, state, plan, skill_root, reviewed_by, evidence)
            if execution["phase"] == "complete":
                return {"changed_files": [], "operation": "noop"}
            if execution["phase"] != "activation_pending" or not plan["activate_on_apply"]:
                raise ValueError("Maintenance execution phase is invalid")
        else:
            current = plan_rules_change(skill_root=skill_root, project_root=layout.project_root,
                rulers_dir=layout.rulers_dir, domain=domain, candidate_dir=plan["candidate_dir"], reason=plan["reason"],
                activate_on_apply=plan["activate_on_apply"],
                readiness_source=plan["readiness_input"]["path"] if plan["readiness_input"] else None)
            if current != plan:
                raise ValueError("Rule plan inputs changed; replan before apply")
            if not (plan["added"] or plan["deleted"] or plan["modified"] or plan["activate_on_apply"]):
                return {"changed_files": [], "operation": "noop"}
            state = _project_state(state, plan)
            prefix = f"{layout.rulers_dir}/{plan['target_dir']}/"
            actions = []
            for name in plan["added"] + plan["modified"]:
                path = checked_path(layout.project_root, plan["candidate_dir"] + "/" + name, required=True)
                if file_sha256(path) != plan["after"][name]:
                    raise ValueError("Candidate changed during apply")
                actions.append(ReplaceAction(prefix + name, path.read_bytes()))
            actions.extend(DeleteAction(prefix + name) for name in plan["deleted"])
            review = {"reviewed_by": reviewed_by.strip(), "evidence": evidence.strip(),
                      "reviewed_at": datetime.now(timezone.utc).isoformat()}
            execution = {"plan_sha256": plan["sha256"], "domain": domain,
                         "activation_scope": plan["activation_scope"], "affected_domains": plan["affected_domains"],
                         "review": review, "review_sha256": identity(review),
                         "phase": "activation_pending" if plan["activate_on_apply"] else "complete",
                         "applied_files": sorted({action.path for action in actions} | {state_relative}),
                         "output_sha256": _state_identity(state)}
            state["maintenance_execution"] = execution
            state["last_operation"] = {"kind": "rules-maintenance", "status": execution["phase"],
                                       "rule_plan_sha256": plan["sha256"], "updated_at": review["reviewed_at"]}
            actions.append(ReplaceAction(state_relative, state_json(state).encode("utf-8")))
            changed = transaction.apply(actions)
            from .rule_loading import validate_links, validate_index_routes
            extras = validate_links(layout, paths=[prefix + name for name in plan["after"]])
            extras.extend(validate_index_routes(layout, index_path=prefix + "INDEX.md", paths=[prefix + name for name in plan["after"]]))
            inspection = inspect_project(project_root=layout.project_root, rulers_dir=layout.rulers_dir)
            blockers = scoped_validation_issues(inspection, [domain], extra_issues=extras, require_active_dependencies=False)
            if blockers:
                raise ValueError("Rule validation failed: " + "; ".join(f"{i.code} {i.message}" for i in blockers))
            if not plan["activate_on_apply"]:
                return {"changed_files": list(changed), "next_action": "review-and-activate", "domain": domain}
    with mutation(layout, transaction_id=activate_id) as transaction:
        state = read_state(layout.rulers_root / "RULERS_STATE.json")
        execution = _check_outputs(layout, state, plan, skill_root, reviewed_by, evidence)
        complete = _complete_state(layout, state, plan, skill_root)
        transaction.apply([ReplaceAction(state_relative, state_json(complete).encode("utf-8"))])
        return {"changed_files": execution["applied_files"], "next_action": "none", "domain": domain,
                "activated": True, "activation": complete["maintenance_execution"]["activation_result"]}
