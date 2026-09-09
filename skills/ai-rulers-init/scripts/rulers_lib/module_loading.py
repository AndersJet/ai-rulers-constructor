"""Consume accepted workspace snapshots without scanning module rule sources."""
from __future__ import annotations

import json
from pathlib import Path

from .module_contracts import checked_path, read_json, file_identity, identity
from .module_rendering import storage_prefix
from .module_exports import read_export_snapshot
from .rule_loading import build_load_bundle, references, resolve_reference
from .reconcile import select_profile_sections
from .validation import build_runtime_context, BUDGETS


def accepted_module(inspection, name):
    state = inspection.state or {}
    if inspection.global_blocked or not inspection.profile_valid or state.get("profile",{}).get("status") != "reviewed":
        raise ValueError("Workspace facts require review or repair")
    record = state.get("modules",{}).get(name)
    if not isinstance(record,dict) or record.get("phase") != "active":
        raise ValueError(f"Module has no accepted snapshot: {name}")
    if not all(record.get("review",{}).get(key) for key in ("reviewed_by","reviewed_at","evidence")):
        raise ValueError(f"Module review is incomplete: {name}")
    layout = inspection.layout
    from .module_git import discover_modules
    topology = discover_modules(layout.project_root,selected={name})["modules"]
    if len(topology) != 1 or not topology[0]["initialized"] or any(topology[0][key] != record["source"][key] for key in ("path","url_hash")):
        raise ValueError(f"Module Git binding changed or is unavailable: {name}")
    code_root = checked_path(layout.project_root,record["source"]["path"])
    if not code_root.is_dir():
        raise ValueError(f"Module code is unavailable: {name}")
    prefix = storage_prefix(layout.rulers_dir,name) + "/"
    for relative in record["snapshot"]["files"]:
        if not relative.startswith(prefix):
            raise ValueError("Module snapshot crosses another module boundary")
        path = checked_path(layout.project_root,relative,required=True)
        metadata = state.get("managed_files",{}).get(relative,{})
        if metadata.get("module") != name or metadata.get("rendered_sha256") != file_identity(path):
            raise ValueError(f"Accepted module snapshot drifted: {name}")
    source_file = record["snapshot"]["source_file"]
    if source_file not in record["snapshot"]["files"]:
        raise ValueError("Source snapshot has no bound hash")
    snapshot = read_export_snapshot(checked_path(layout.project_root,source_file,required=True))
    if snapshot.get("content_id") != record["snapshot"]["content_id"]:
        raise ValueError("Snapshot content identity mismatch")
    for relative, expected in snapshot["evidence"].items():
        if file_identity(checked_path(code_root,relative,required=True)) != expected:
            raise ValueError(f"Module code evidence changed: {name}/{relative}")
    from .module_adjustments import effective_export, empty_adjustments
    adjustment_file = record.get("adjustments_file")
    overlay = empty_adjustments()
    if adjustment_file:
        path = checked_path(layout.project_root,adjustment_file,required=True)
        metadata = state.get("managed_files",{}).get(adjustment_file,{})
        if metadata.get("module") != name or metadata.get("rendered_sha256") != file_identity(path):
            raise ValueError("Workspace adjustment drift")
        overlay = read_json(path)
    if identity({"source":snapshot["content_id"],"adjustments":overlay}) != record["snapshot"]["effective_id"]:
        raise ValueError("Effective module identity mismatch")
    return record,effective_export(snapshot,overlay)


def module_context(inspection, *, names=(), domains=(), workspace_domains=()):
    context = build_runtime_context(inspection,requested_domains=workspace_domains if names else domains)
    registered = (inspection.state or {}).get("modules",{})
    context["available_modules"] = sorted(registered)[:12]
    context["module_count"] = len(registered)
    context["module_load"] = {}
    for name in names:
        try:
            record,snapshot = accepted_module(inspection,name)
            chosen = set(domains) or {rule["domain"] for rule in snapshot["rules"].values()}
            indexes = [path for path,rule in snapshot["rules"].items() if rule["domain"] in chosen and Path(path).name == "INDEX.md"]
            context["module_load"][name] = {"code_root":record["source"]["path"],
                "profile":storage_prefix(inspection.layout.rulers_dir,name)+"/PROFILE.md",
                "indexes":[storage_prefix(inspection.layout.rulers_dir,name)+"/rules/"+path for path in indexes]}
        except (ValueError,KeyError,TypeError) as exc:
            context["blocked"] = True
            context["next_action"] = "manual-module-sync-or-repair"
            context.setdefault("module_errors",[]).append({"module":name,"message":str(exc)})
    return context


def module_bundle(inspection, *, names, domains=(), rules=(), workspace_domains=(), workspace_rules=()):
    base = build_load_bundle(inspection,domains=workspace_domains,rules=workspace_rules)
    contents = [base["content"]]
    files = list(base["files"])
    available = []
    matched = set()
    commands = []
    for name in sorted(set(names)):
        record,snapshot = accepted_module(inspection,name)
        chosen = set(domains) or {rule["domain"] for rule in snapshot["rules"].values()}
        if not chosen <= {rule["domain"] for rule in snapshot["rules"].values()}:
            raise ValueError(f"Unknown module domain selection: {name}")
        prefix = storage_prefix(inspection.layout.rulers_dir,name)
        allowed = {prefix+"/rules/"+path:path for path in snapshot["rules"]}
        queue = [path for path,source in allowed.items() if snapshot["rules"][source]["domain"] in chosen and Path(source).name=="INDEX.md"]
        for requested in rules:
            relative = requested.removeprefix(name+":")
            if relative in snapshot["rules"] and snapshot["rules"][relative]["domain"] in chosen:
                queue.append(prefix+"/rules/"+relative); matched.add(requested)
        seen = set()
        contents.append(f"## Module {name}\nCode root: {record['source']['path']}\n")
        while queue:
            relative = queue.pop(0)
            if relative in seen:
                continue
            seen.add(relative)
            path = checked_path(inspection.layout.project_root,relative,required=True)
            text = path.read_text(encoding="utf-8")
            files.append(relative); contents.append(f"<!-- {relative} -->\n{text}")
            dependencies,_ = references(text)
            for value in dependencies:
                target = resolve_reference(inspection.layout,path,value)
                if target is None or target.name in {"AGENTS.md","RULERS_STATE.json"}:
                    continue
                dependency = target.relative_to(inspection.layout.project_root).as_posix()
                if dependency in allowed:
                    queue.append(dependency)
                elif dependency != prefix+"/PROFILE.md" and dependency not in base["files"]:
                    raise ValueError(f"Dependency outside exported module: {dependency}")
        profile_path = prefix+"/PROFILE.md"
        profile = select_profile_sections(snapshot["profile"],scopes={"core",*chosen},always_sections=["项目身份"])
        contents.append(f"<!-- {profile_path} -->\n{profile}");files.append(profile_path)
        available.extend(name+":"+path for path,rule in snapshot["rules"].items() if rule["domain"] in chosen)
        for command in snapshot["commands"]:
            commands.append({**command,"module":name,"cwd":str(Path(record["source"]["path"])/command.get("cwd","."))})
    if set(rules)-matched:
        raise ValueError("Requested rule is outside selected module/domain")
    contents.append("## Module validation commands\n"+json.dumps(commands,ensure_ascii=False,indent=2))
    content = "\n\n".join(contents)
    size = len(content.encode("utf-8"))
    return {"files":files,"available_rules":available,"commands":commands,"content":content,
            "bytes":size,"within_budget":size<=BUDGETS["fixed_chain_bytes"]}
