"""Reviewed, file-granular domain maintenance without a second State."""
from __future__ import annotations

import hashlib
import difflib
import json
from pathlib import Path
from datetime import datetime, timezone

from .domains import load_domain_registry, expand_reverse_dependencies, effective_domain_configs, nested_domain_dirs
from .paths import resolve_layout, resolve_safe_child
from .state import read_state, state_json, file_sha256, text_sha256
from .mutations import mutation
from .transactions import ReplaceAction, DeleteAction
from .validation import validate_rule_metadata_text, validate_project


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
            result[path.relative_to(root).as_posix()] = file_sha256(path)
    return result


def _digest(plan):
    return text_sha256(json.dumps({k: v for k, v in plan.items() if k != "sha256"}, sort_keys=True, ensure_ascii=False))


def plan_rules_change(*, skill_root: Path, project_root: Path, rulers_dir: str,
                      domain: str, candidate_dir: str, reason: str) -> dict:
    if not reason.strip():
        raise ValueError("Rule maintenance requires a reason or failure evidence")
    layout = resolve_layout(project_root, rulers_dir)
    registry = load_domain_registry(skill_root)
    if domain not in registry or domain == "core":
        raise ValueError("Choose a registered project domain; core is maintained by template upgrade")
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_state(state_path)
    if state["profile"]["status"] != "reviewed":
        raise ValueError("Review project facts before maintaining domain rules")
    candidate = resolve_safe_child(layout.project_root, candidate_dir)
    if candidate == layout.rulers_root or layout.rulers_root in candidate.parents:
        raise ValueError("Stage candidates outside the installed rulers directory")
    target = resolve_safe_child(layout.rulers_root, registry[domain]["target_dir"])
    excluded_dirs = nested_domain_dirs(domain, effective_domain_configs(registry, state))
    for excluded in excluded_dirs:
        copied = candidate / excluded
        if copied.exists() or copied.is_symlink():
            installed = target / excluded
            if _files(copied) != (_files(installed) if installed.exists() else {}):
                raise ValueError(f"Candidate modifies another domain subtree: {excluded}; maintain it separately")
    desired = _files(candidate, excluded_dirs=excluded_dirs)
    if "INDEX.md" not in desired:
        raise ValueError("Domain candidate needs INDEX.md")
    for name in desired:
        text = (candidate / name).read_text(encoding="utf-8")
        if "AI_FILL" in text or "{{RULERS_DIR}}" in text or validate_rule_metadata_text(text, name):
            raise ValueError(f"Incomplete rule candidate: {name}")
    old = _files(target, excluded_dirs=excluded_dirs) if target.exists() else {}
    result = {
        "operation": "rules-maintenance", "project_root": str(layout.project_root),
        "rulers_dir": layout.rulers_dir, "domain": domain,
        "target_dir": registry[domain]["target_dir"],
        "candidate_dir": candidate.relative_to(layout.project_root).as_posix(),
        "excluded_dirs": list(excluded_dirs),
        "reason": reason, "state_sha256": file_sha256(state_path),
        "before": old, "after": desired,
        "added": sorted(desired.keys() - old.keys()), "deleted": sorted(old.keys() - desired.keys()),
        "modified": sorted(name for name in old.keys() & desired.keys() if old[name] != desired[name]),
    }
    result["patch"] = "".join(
        "".join(difflib.unified_diff(
            (target / name).read_text(encoding="utf-8").splitlines(keepends=True) if name in old else [],
            (candidate / name).read_text(encoding="utf-8").splitlines(keepends=True) if name in desired else [],
            fromfile=f"{registry[domain]['target_dir']}/{name}",
            tofile=f"candidate/{name}",
        ))
        for name in sorted(set(result["added"] + result["deleted"] + result["modified"]))
    )
    result["sha256"] = _digest(result)
    return result


def apply_rules_change(*, plan: dict, skill_root: Path, reviewed_by: str, evidence: str) -> dict:
    if not reviewed_by.strip() or not evidence.strip():
        raise ValueError("Rule changes require reviewer and evidence")
    if plan.get("sha256") != _digest(plan):
        raise ValueError("Rule maintenance plan digest mismatch")
    layout = resolve_layout(Path(plan["project_root"]), plan["rulers_dir"])
    with mutation(layout) as transaction:
        recorded = read_state(layout.rulers_root / "RULERS_STATE.json")
        if recorded.get("last_operation", {}).get("rule_plan_sha256") == plan["sha256"]:
            target = resolve_safe_child(layout.rulers_root, plan["target_dir"])
            candidate = resolve_safe_child(layout.project_root, plan["candidate_dir"])
            if _files(target, excluded_dirs=plan.get("excluded_dirs", ())) == plan["after"] and _files(candidate, excluded_dirs=plan.get("excluded_dirs", ())) == plan["after"]:
                return {"changed_files": [], "operation": "noop"}
            raise ValueError("Applied rule output or candidate changed; replan")
        current = plan_rules_change(skill_root=skill_root, project_root=layout.project_root,
            rulers_dir=layout.rulers_dir, domain=plan["domain"], candidate_dir=plan["candidate_dir"], reason=plan["reason"])
        if current != plan:
            raise ValueError("Rule plan inputs changed; replan before apply")
        if not (plan["added"] or plan["deleted"] or plan["modified"]):
            return {"changed_files": [], "operation": "noop"}
        state_path = layout.rulers_root / "RULERS_STATE.json"
        state = read_state(state_path)
        registry = load_domain_registry(skill_root)
        config = registry[plan["domain"]]
        prefix = f"{layout.rulers_dir}/{config['target_dir']}/"
        inventory = state["managed_files"]
        actions = []
        for name in plan["added"] + plan["modified"]:
            data = (resolve_safe_child(layout.project_root, plan["candidate_dir"]) / name).read_bytes()
            if "sha256:" + hashlib.sha256(data).hexdigest() != plan["after"][name]:
                raise ValueError("Candidate content changed during apply")
            actions.append(ReplaceAction(prefix + name, data))
        for name in plan["deleted"]:
            actions.append(DeleteAction(prefix + name))
            inventory.pop(prefix + name, None)
        for name, digest in plan["after"].items():
            inventory[prefix + name] = {"ownership": "managed", "project_owned": True,
                "template_id": f"generated/{plan['domain']}/{name}",
                "source_sha256": digest, "rendered_sha256": digest}
        value = state["domains"].setdefault(plan["domain"], {})
        value.update(target_dir=config["target_dir"], required_files=sorted(plan["after"]),
            requires_active=config["requires_active"], generated=True, detected=True, retired=False,
            level=0, review_status="draft", level3_ready=False,
            removed_files=sorted((set(value.get("removed_files", [])) | set(plan["deleted"])) - set(plan["after"])),
            review={"reviewed_by": None, "reviewed_at": None, "evidence": None})
        for dependent in expand_reverse_dependencies({plan["domain"]}, registry) - {plan["domain"]}:
            if dependent in state["domains"]:
                state["domains"][dependent].update(level=0, review_status="draft", level3_ready=False)
        if state["phase"] == "profile_reviewed":
            state["phase"] = "rules_candidate"
        state["last_operation"] = {"kind": "rules-maintenance", "status": "complete", "reason": plan["reason"], "rule_plan_sha256": plan["sha256"],
            "reviewed_by": reviewed_by, "evidence": evidence, "reviewed_at": datetime.now(timezone.utc).isoformat()}
        actions.append(ReplaceAction(f"{layout.rulers_dir}/RULERS_STATE.json", state_json(state).encode("utf-8")))
        changed = transaction.apply(actions)
        errors = validate_project(mode="candidate", project_root=layout.project_root, rulers_dir=layout.rulers_dir)
        from .rule_loading import validate_links, validate_index_routes
        errors.extend(validate_links(layout, paths=[prefix + name for name in plan["after"]]))
        errors.extend(validate_index_routes(layout, index_path=prefix + "INDEX.md", paths=[prefix + name for name in plan["after"]]))
        if any(i.severity == "error" for i in errors):
            raise ValueError("Rule validation failed: " + "; ".join(i.message for i in errors))
        return {"changed_files": list(changed), "next_action": "review-and-activate", "domain": plan["domain"]}
