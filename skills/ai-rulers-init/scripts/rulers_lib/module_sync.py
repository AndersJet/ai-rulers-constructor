"""Manual, reviewed source-to-workspace adoption with content-bound plans."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .module_contracts import MODULE_PLAN_SCHEMA_VERSION, require_protocol, checked_path, read_json, identity, file_identity, content_hash, json_bytes, engine_identity
from .module_adjustments import empty_adjustments, read_adjustments, adjustment_conflicts, effective_export
from .module_exports import capture_export, read_export_snapshot
from .module_diffs import review_changes
from .module_git import discover_modules
from .module_rendering import render_module, storage_prefix
from .mutations import mutation
from .paths import resolve_layout
from .state import state_json
from .transactions import ReplaceAction, DeleteAction


def bound_sources(layout, state, names, source_workspace=None):
    registered = state.get("modules", {})
    selected = sorted(set(names)) if names else sorted(registered)
    discovered = {m["name"]: m for m in discover_modules(source_workspace or layout.project_root,selected=set(selected))["modules"]}
    if not selected:
        raise ValueError("No modules registered")
    result = {}
    for name in selected:
        if name not in registered or name not in discovered:
            raise ValueError(f"Module registration is unavailable: {name}")
        source = registered[name]["source"]
        current = discovered[name]
        if not current["initialized"]:
            raise ValueError(f"Module is not initialized: {name}")
        if any(source[key] != current[key] for key in ("path", "url_hash")):
            raise ValueError(f"Module Git binding changed; register it again: {name}")
        result[name] = {"source": source, "git": current}
    return result


def sync_plan(*, project_root: Path, rulers_dir: str, names: list[str], operation="sync", adjustments_path=None, completion=None, _source_workspace=None) -> dict:
    layout = resolve_layout(project_root, rulers_dir)
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_json(state_path)
    from .validation import inspect_project
    inspection = inspect_project(project_root=layout.project_root,rulers_dir=layout.rulers_dir)
    if inspection.global_blocked or not inspection.profile_valid or state.get("profile", {}).get("status") != "reviewed":
        raise ValueError("Review workspace facts before module adoption")
    sources = bound_sources(layout,state,names,_source_workspace)
    if completion:
        for relative,digest in completion.get("workspace_inputs",{}).items():
            if file_identity(checked_path(layout.project_root,relative,required=True)) != digest:
                raise ValueError("Legacy workspace inputs changed; replan migration")
        progress = state["modules"].get(completion["name"],{}).get("migration",{})
        if progress.get("plan_digest") != completion["migration_digest"] or completion["name"] not in sources:
            raise ValueError("Migration completion does not match its checkpoint")
        if "core" in completion["retire_domains"] or any(d not in state["domains"] for d in completion["retire_domains"]):
            raise ValueError("Invalid migration retirement scope")
    if adjustments_path and len(sources) != 1:
        raise ValueError("An adjustment definition applies to one module at a time")
    if operation == "adjust" and not adjustments_path:
        raise ValueError("Adjustment plan requires --adjustments")
    captures = {}
    adjustments = {}
    adjustment_inputs = {}
    effective_ids = {}
    expected = {}
    changed = []
    conflicts = []
    changes = {}
    for name, binding in sources.items():
        source = binding["source"]
        record = state["modules"][name]
        if operation == "adjust":
            source_file = record.get("snapshot",{}).get("source_file")
            if not source_file:
                raise ValueError("Sync a module before adjusting it")
            snapshot = read_export_snapshot(checked_path(layout.project_root,source_file,required=True))
        else:
            snapshot = capture_export(project_root=checked_path(layout.project_root, source["path"]),
                                      rulers_dir=source["rulers_dir"], manifest=source["manifest"],
                                      code_root=checked_path(_source_workspace,source["path"]) if _source_workspace else None)
        captures[name] = snapshot
        adjustment_file = record.get("adjustments_file")
        if adjustment_file:
            path = checked_path(layout.project_root,adjustment_file,required=True)
            expected[adjustment_file] = file_identity(path)
            if expected[adjustment_file] != state.get("managed_files",{}).get(adjustment_file,{}).get("rendered_sha256"):
                conflicts.append({"module":name,"path":adjustment_file,"reason":"adjustment-file-drift"})
        if adjustments_path:
            overlay, input_hashes = read_adjustments(layout.project_root,adjustments_path,snapshot)
            adjustment_inputs.update(input_hashes)
        else:
            overlay = read_json(checked_path(layout.project_root,adjustment_file,required=True)) if adjustment_file else empty_adjustments()
        adjustments[name] = overlay
        previous_file = record.get("snapshot", {}).get("source_file")
        previous = read_export_snapshot(checked_path(layout.project_root,previous_file,required=True)) if previous_file else None
        old_overlay = read_json(checked_path(layout.project_root,adjustment_file,required=True)) if adjustment_file else empty_adjustments()
        changes[name] = review_changes(effective_export(previous,old_overlay) if previous else None,effective_export(snapshot,overlay))
        effective_ids[name] = identity({"source":snapshot["content_id"],"adjustments":overlay})
        conflicts.extend({"module":name,**conflict} for conflict in adjustment_conflicts(snapshot,overlay))
        for path in record.get("snapshot", {}).get("files", []):
            target = checked_path(layout.project_root,path)
            expected[path] = file_identity(target)
            metadata = state.get("managed_files", {}).get(path, {})
            if expected[path] != metadata.get("rendered_sha256"):
                conflicts.append({"module":name,"path":path,"reason":"imported-file-drift"})
        if record.get("phase") != "active" or record.get("snapshot", {}).get("effective_id") != effective_ids[name]:
            changed.append(name)
    plan = {"module_plan_version":MODULE_PLAN_SCHEMA_VERSION,"operation":operation,"project_root":str(layout.project_root),
            "rulers_dir":layout.rulers_dir,"names":sorted(sources),"engine_id":engine_identity(),"completion":completion,"state_hash":file_identity(state_path),
            "sources":sources,"captures":captures,"expected_files":expected,
            "adjustments":adjustments,"adjustments_path":adjustments_path,"adjustment_inputs":adjustment_inputs,"effective_ids":effective_ids,
            "changed_modules":changed,"changes":changes,"conflicts":conflicts,"requires_review":bool(changed or completion)}
    plan["digest"] = identity(plan)
    return plan


def apply_sync(plan: dict, *, reviewed_by: str, evidence: str, _source_workspace=None) -> dict:
    require_protocol(plan, "module_plan_version", MODULE_PLAN_SCHEMA_VERSION)
    if plan.get("digest") != identity({k:v for k,v in plan.items() if k != "digest"}):
        raise ValueError("Module plan digest mismatch")
    if plan["requires_review"] and (not reviewed_by.strip() or not evidence.strip()):
        raise ValueError("Workspace adoption requires reviewer and evidence")
    layout = resolve_layout(Path(plan["project_root"]),plan["rulers_dir"])
    with mutation(layout) as transaction:
        state_path = layout.rulers_root / "RULERS_STATE.json"
        state = read_json(state_path)
        current = sync_plan(project_root=layout.project_root,rulers_dir=layout.rulers_dir,names=plan["names"],operation=plan["operation"],adjustments_path=plan.get("adjustments_path"),completion=plan.get("completion"),_source_workspace=_source_workspace)
        if state.get("last_operation",{}).get("module_plan_digest") == plan["digest"] and not current["changed_modules"] and not current["conflicts"]:
            return {"operation":"noop","changed_files":[]}
        if current != plan:
            raise ValueError("Sync inputs changed; replan")
        if plan["conflicts"]:
            raise ValueError("Module sync conflicts require explicit review and revised adjustments: "+str(plan["conflicts"]))
        if not plan["changed_modules"] and not plan.get("completion"):
            return {"operation":"noop","changed_files":[]}
        actions = []
        paths = []
        for name in plan["changed_modules"]:
            record = state["modules"][name]
            snapshot = plan["captures"][name]
            rendered = render_module(snapshot,name=name,code_root=record["source"]["path"],rulers_dir=layout.rulers_dir,adjustments=plan["adjustments"][name])
            old = set(record.get("snapshot",{}).get("files",[]))
            adjustment_file = storage_prefix(layout.rulers_dir,name).rsplit("/",1)[0]+"/adjustments.json"
            if Path(adjustment_file).name and (layout.project_root/adjustment_file).exists() and record.get("adjustments_file") != adjustment_file:
                raise ValueError("Unmanaged adjustment target conflict")
            adjustment_content = json_bytes(plan["adjustments"][name])
            actions.append(ReplaceAction(adjustment_file,adjustment_content))
            state["managed_files"][adjustment_file] = {"ownership":"managed","project_owned":True,"module":name,
                "template_id":"workspace-adjustment","source_sha256":content_hash(adjustment_content),"rendered_sha256":content_hash(adjustment_content)}
            record["adjustments_file"] = adjustment_file
            for path in rendered:
                target = checked_path(layout.project_root,path)
                if target.exists() and path not in old:
                    raise ValueError(f"Unmanaged module target conflict: {path}")
            for path in old - rendered.keys():
                actions.append(DeleteAction(path)); state["managed_files"].pop(path,None)
            for path, content in rendered.items():
                actions.append(ReplaceAction(path,content))
                state["managed_files"][path] = {"ownership":"managed","project_owned":True,"module":name,
                    "template_id":"module-import","source_sha256":content_hash(content),"rendered_sha256":content_hash(content)}
            record["snapshot"] = {"content_id":snapshot["content_id"],"effective_id":plan["effective_ids"][name],"capture_id":snapshot["capture_id"],
                                  "source_file":storage_prefix(layout.rulers_dir,name)+"/source.json","files":sorted(rendered)}
            record["phase"] = "active"
            record["review"] = {"reviewed_by":reviewed_by,"reviewed_at":datetime.now(timezone.utc).isoformat(),"evidence":evidence}
            paths.extend(rendered)
        if plan.get("completion"):
            completion = plan["completion"]
            for domain in completion["retire_domains"]:
                state["domains"][domain].update(level=0,review_status="draft",retired=True,level3_ready=False)
            state["modules"][completion["name"]]["migration"]["phase"] = "complete"
        state["last_operation"] = {"kind":"module-sync","status":"complete","module_plan_digest":plan["digest"]}
        actions.append(ReplaceAction(f"{layout.rulers_dir}/RULERS_STATE.json",state_json(state).encode("utf-8")))
        changed = transaction.apply(actions)
        from .rule_loading import validate_links, validate_index_routes
        errors = validate_links(layout,paths=[path for path in paths if path.endswith(".md") and not path.endswith("/PROFILE.md")])
        for name in plan["changed_modules"]:
            effective = effective_export(plan["captures"][name],plan["adjustments"][name])
            for domain in {rule["domain"] for rule in effective["rules"].values()}:
                group = [p for p,r in effective["rules"].items() if r["domain"] == domain]
                indexes = [p for p in group if Path(p).name == "INDEX.md"]
                if not indexes:
                    raise ValueError("Workspace adjustments removed required INDEX navigation")
                prefix = storage_prefix(layout.rulers_dir,name)+"/rules/"
                errors.extend(validate_index_routes(layout,index_path=prefix+min(indexes,key=lambda p:len(Path(p).parts)),paths=[prefix+p for p in group]))
        if errors:
            raise ValueError("Imported rules failed validation: "+"; ".join(e.message for e in errors))
        return {"operation":"sync","changed_files":list(changed),"modules":plan["changed_modules"]}
