"""Registration plans bind direct Git modules to independently owned rule sources."""
from __future__ import annotations

from pathlib import Path

from .module_contracts import MODULE_PLAN_SCHEMA_VERSION, require_protocol, read_json, identity, file_identity, checked_path
from .module_git import discover_modules
from .mutations import mutation, write_text
from .paths import resolve_layout
from .state import state_json


def module_status(*, project_root: Path, rulers_dir: str) -> dict:
    layout = resolve_layout(project_root, rulers_dir)
    topology = discover_modules(layout.project_root)
    path = layout.rulers_root / "RULERS_STATE.json"
    state = read_json(path) if path.is_file() else {}
    return {"discovered": topology["modules"], "registered": state.get("modules", {})}


def registration_plan(*, project_root: Path, rulers_dir: str, names: list[str],
                      source_rulers="documents/rulers", manifest="MODULE_EXPORT.json", _topology_root=None) -> dict:
    layout = resolve_layout(project_root, rulers_dir)
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_json(state_path)
    topology = discover_modules(_topology_root or layout.project_root)
    selected = sorted(set(names)) if names else [m["name"] for m in topology["modules"]]
    definitions = {m["name"]: m for m in topology["modules"]}
    if not selected or any(name not in definitions for name in selected):
        raise ValueError("Select existing direct Git submodules")
    checked_path(layout.project_root, source_rulers)
    checked_path(layout.project_root, manifest)
    desired = {}
    for name in selected:
        definition = definitions[name]
        previous = state.get("modules", {}).get(name, {})
        source = {"path": definition["path"], "url_hash": definition["url_hash"],
                  "rulers_dir": source_rulers, "manifest": manifest}
        desired[name] = previous if previous.get("source") == source else {
            **previous, "source": source, "phase": "registered" if definition["initialized"] else "unavailable"}
    plan = {"module_plan_version": MODULE_PLAN_SCHEMA_VERSION, "operation": "register", "project_root": str(layout.project_root),
            "rulers_dir": layout.rulers_dir, "names": selected, "source_rulers": source_rulers, "manifest": manifest,
            "state_hash": file_identity(state_path), "topology": topology, "desired": desired}
    plan["digest"] = identity(plan)
    return plan


def apply_registration(plan: dict, *, reviewed_by: str, evidence: str) -> dict:
    require_protocol(plan, "module_plan_version", MODULE_PLAN_SCHEMA_VERSION)
    if not reviewed_by.strip() or not evidence.strip():
        raise ValueError("Registration requires reviewer and evidence")
    if plan.get("digest") != identity({k:v for k,v in plan.items() if k != "digest"}):
        raise ValueError("Module plan digest mismatch")
    layout = resolve_layout(Path(plan["project_root"]), plan["rulers_dir"])
    with mutation(layout):
        state_path = layout.rulers_root / "RULERS_STATE.json"
        state = read_json(state_path)
        if state.get("last_operation", {}).get("module_plan_digest") == plan["digest"]:
            if discover_modules(layout.project_root) == plan["topology"] and all(state.get("modules", {}).get(name) == value for name, value in plan["desired"].items()):
                return {"changed_files": [], "operation": "noop"}
            raise ValueError("Registration changed; replan")
        current = registration_plan(project_root=layout.project_root, rulers_dir=layout.rulers_dir,
            names=plan["names"], source_rulers=plan["source_rulers"], manifest=plan["manifest"])
        if current != plan:
            raise ValueError("Registration inputs changed; replan")
        if all(state.get("modules", {}).get(name) == value for name,value in plan["desired"].items()):
            return {"changed_files": [], "operation": "noop"}
        state.setdefault("modules", {}).update(plan["desired"])
        state["last_operation"] = {"kind": "module-register", "status": "complete", "module_plan_digest": plan["digest"],
                                   "reviewed_by": reviewed_by, "evidence": evidence}
        write_text(state_path, state_json(state))
        return {"changed_files": [f"{layout.rulers_dir}/RULERS_STATE.json"], "operation": "register"}
