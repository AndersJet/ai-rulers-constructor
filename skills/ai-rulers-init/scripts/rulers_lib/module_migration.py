"""Two-stage migration: prepare a draft module source, then switch the workspace atomically."""
from __future__ import annotations

import tempfile
from pathlib import Path

from .module_contracts import MODULE_PLAN_SCHEMA_VERSION, require_protocol, checked_path, read_json, identity, file_identity, content_hash, json_bytes
from .module_exports import capture_export
from .module_sync import bound_sources, sync_plan, apply_sync
from .mutations import mutation, write_text
from .paths import resolve_layout
from .runtime_files import runtime_files
from .state import create_initial_state, state_json
from .transactions import ReplaceAction, inspect_incomplete_transaction, restore_transaction
from .domains import load_domain_registry
from .plans import _tree_fingerprint, _policy_fact


def _candidate(root,relative):
    folder = checked_path(root,relative)
    if not folder.is_dir():
        raise ValueError("Migration requires a complete portable candidate directory")
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("Migration candidate contains a symlink")
        if path.is_file():
            name = path.relative_to(folder).as_posix()
            if name.startswith(("scripts/","core/")) or (path.suffix != ".md" and name != "MODULE_EXPORT.json"):
                raise ValueError("Candidate contains framework or unsupported artifacts")
            result[name] = path.read_text(encoding="utf-8")
    if not {"PROJECT_PROFILE.md","MODULE_EXPORT.json"} <= result.keys():
        raise ValueError("Migration candidate requires portable Profile and export manifest")
    return result


def _source_materialization(*,skill_root,source_layout,candidate):
    import json
    manifest = json.loads(candidate["MODULE_EXPORT.json"])
    domains = sorted({rule["domain"] for rule in manifest["rules"]})
    registry = load_domain_registry(skill_root)
    files = runtime_files(skill_root=skill_root,layout=source_layout,policy_id="project-native")
    prefix = source_layout.rulers_dir+"/"
    for name,text in candidate.items():
        files[prefix+name] = text.encode("utf-8")
    state = create_initial_state(rulers_dir=source_layout.rulers_dir,policy_id="project-native",detected_domains=domains)
    state["phase"] = "profile_draft"
    state["policy"] = _policy_fact(skill_root,"project-native")
    state["template"] = {"version":state["template"]["version"],"fingerprint":_tree_fingerprint(skill_root)}
    for domain in domains:
        target = registry[domain]["target_dir"]
        names = []
        for rule in manifest["rules"]:
            if rule["domain"] == domain:
                if not rule["path"].startswith(target+"/"):
                    raise ValueError("Migration rule layout must support independent domain registration")
                names.append(rule["path"][len(target)+1:])
        state["domains"][domain]["required_files"] = sorted(names)
    for path,content in files.items():
        if not path.startswith(prefix):
            continue
        name = path[len(prefix):]
        state["managed_files"][path] = {"ownership":"collaborative" if name=="PROJECT_PROFILE.md" else "managed",
            "project_owned":name in candidate and name != "PROJECT_PROFILE.md",
            "template_id":name,"source_sha256":content_hash(content),"rendered_sha256":content_hash(content)}
    state["last_operation"] = {"kind":"module-source-prepare","status":"complete"}
    files[prefix+"RULERS_STATE.json"] = state_json(state).encode("utf-8")
    return files


def migration_plan(*,skill_root,project_root,rulers_dir,name,candidate_dir,retire_domains):
    layout = resolve_layout(project_root,rulers_dir)
    state_path = layout.rulers_root/"RULERS_STATE.json"
    state = read_json(state_path)
    binding = bound_sources(layout,state,[name])[name]
    source = binding["source"]
    if source["manifest"] != "MODULE_EXPORT.json":
        raise ValueError("Initial migration uses MODULE_EXPORT.json; re-register the source manifest")
    child = checked_path(layout.project_root,source["path"])
    child_layout = resolve_layout(child,source["rulers_dir"])
    if child_layout.rulers_root.exists() and any(path.is_file() for path in child_layout.rulers_root.rglob("*")):
        raise ValueError("Source rules already exist; use explicit export/sync rather than overwrite")
    if "core" in retire_domains or any(domain not in state["domains"] for domain in retire_domains):
        raise ValueError("Only explicitly selected existing workspace domains may be retired")
    candidate = _candidate(layout.project_root,candidate_dir)
    materialized = _source_materialization(skill_root=skill_root,source_layout=child_layout,candidate=candidate)
    with tempfile.TemporaryDirectory(prefix="module-source-projection-") as td:
        projection = Path(td).resolve()
        for path,content in materialized.items():
            target = checked_path(projection,path)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(content)
        exported = capture_export(project_root=projection,rulers_dir=source["rulers_dir"],code_root=child)
    workspace_inputs = {f"{layout.rulers_dir}/PROJECT_PROFILE.md":file_identity(layout.rulers_root/"PROJECT_PROFILE.md")}
    for domain in retire_domains:
        value = state["domains"][domain]
        for filename in value.get("required_files",[]):
            relative = f"{layout.rulers_dir}/{value['target_dir']}/{filename}"
            workspace_inputs[relative] = file_identity(checked_path(layout.project_root,relative,required=True))
    plan = {"module_plan_version":MODULE_PLAN_SCHEMA_VERSION,"operation":"migrate","project_root":str(layout.project_root),
            "rulers_dir":rulers_dir,"name":name,"template_fingerprint":_tree_fingerprint(skill_root),"candidate_dir":candidate_dir,
            "candidate_hash":identity(candidate),"state_hash":file_identity(state_path),"binding":binding,
            "source_files":{path:content.decode("utf-8") for path,content in materialized.items()},
            "source_expected":{path:file_identity(checked_path(child,path)) for path in materialized},
            "export_content_id":exported["content_id"],"evidence":exported["evidence"],
            "retire_domains":sorted(set(retire_domains)),"workspace_inputs":workspace_inputs}
    plan["digest"] = identity(plan)
    return plan


def apply_migration(plan,*,skill_root,reviewed_by,evidence,stage="complete"):
    require_protocol(plan, "module_plan_version", MODULE_PLAN_SCHEMA_VERSION)
    if not reviewed_by.strip() or not evidence.strip():
        raise ValueError("Migration requires explicit review")
    if plan.get("digest") != identity({k:v for k,v in plan.items() if k!="digest"}):
        raise ValueError("Migration plan digest mismatch")
    if plan["template_fingerprint"] != _tree_fingerprint(skill_root):
        raise ValueError("Migration templates changed; replan")
    layout = resolve_layout(Path(plan["project_root"]),plan["rulers_dir"])
    state_path = layout.rulers_root/"RULERS_STATE.json"
    workspace_before = file_identity(state_path)
    changed_files = []
    state = read_json(state_path)
    progress = state["modules"][plan["name"]].get("migration",{})
    if progress.get("plan_digest")==plan["digest"] and progress.get("phase")=="complete":
        return {"changed_files":[],"operation":"noop"}
    if progress.get("plan_digest") != plan["digest"]:
        current = migration_plan(skill_root=skill_root,project_root=layout.project_root,rulers_dir=layout.rulers_dir,
            name=plan["name"],candidate_dir=plan["candidate_dir"],retire_domains=plan["retire_domains"])
        if current != plan:
            raise ValueError("Migration inputs changed; replan")
        with mutation(layout):
            if file_identity(state_path) != plan["state_hash"]:
                raise ValueError("Workspace changed before migration checkpoint")
            state["modules"][plan["name"]]["migration"] = {"phase":"prepared","plan_digest":plan["digest"]}
            write_text(state_path,state_json(state))
    for relative,digest in plan["workspace_inputs"].items():
        if file_identity(checked_path(layout.project_root,relative,required=True)) != digest:
            raise ValueError("Legacy workspace inputs changed; replan migration")
    if identity(_candidate(layout.project_root,plan["candidate_dir"])) != plan["candidate_hash"]:
        raise ValueError("Portable candidate changed; preserve work and replan")
    state = read_json(state_path)
    binding = bound_sources(layout,state,[plan["name"]])[plan["name"]]
    if binding["source"] != plan["binding"]["source"] or binding["git"]["head"] != plan["binding"]["git"]["head"]:
        raise ValueError("Module identity or code version changed during migration")
    child = checked_path(layout.project_root,binding["source"]["path"])
    child_layout = resolve_layout(child,binding["source"]["rulers_dir"])
    for path,digest in plan["evidence"].items():
        if file_identity(checked_path(child,path,required=True)) != digest:
            raise ValueError("Code evidence changed during migration")
    files = {path:text.encode("utf-8") for path,text in plan["source_files"].items()}
    source_state_path = child_layout.rulers_root/"RULERS_STATE.json"
    # State may already be written when a process dies before transaction cleanup.
    incomplete = inspect_incomplete_transaction(child_layout)
    if incomplete:
        if incomplete.transaction_id != plan["digest"][7:23] or any(action.path not in files for action in incomplete.actions):
            raise ValueError("Unrelated source transaction requires separate repair")
        restore_transaction(layout=child_layout,transaction_id=incomplete.transaction_id,
            expected_lock_sha256=incomplete.lock_sha256,expected_lock_nonce=incomplete.lock_nonce)
    source_state = read_json(source_state_path) if source_state_path.is_file() else None
    if not source_state or source_state.get("migration_origin") != plan["digest"]:
        with mutation(child_layout,transaction_id=plan["digest"][7:23]) as transaction:
            for path,expected in plan["source_expected"].items():
                if file_identity(checked_path(child,path)) != expected:
                    raise ValueError("Source target changed; do not overwrite it")
            source_state = read_json_from_bytes(files[child_layout.rulers_dir+"/RULERS_STATE.json"])
            source_state["migration_origin"] = plan["digest"]
            files[child_layout.rulers_dir+"/RULERS_STATE.json"] = state_json(source_state).encode("utf-8")
            source_changes = transaction.apply([ReplaceAction(path,content) for path,content in files.items()])
            changed_files.extend(binding["source"]["path"]+"/"+path for path in source_changes)
    for path,content in files.items():
        if path.endswith("/RULERS_STATE.json"):
            continue
        if file_identity(checked_path(child,path,required=True)) != content_hash(content):
            raise ValueError("Prepared source changed; replan without overwriting it")
    snapshot = capture_export(project_root=child,rulers_dir=child_layout.rulers_dir)
    if snapshot["content_id"] != plan["export_content_id"]:
        raise ValueError("Prepared source differs from reviewed projection")
    if stage=="source":
        with mutation(layout):
            state = read_json(state_path)
            state["modules"][plan["name"]]["migration"]["phase"] = "source-ready"
            write_text(state_path,state_json(state))
        return {"stage":"source-ready","changed_files":changed_files + ([f"{layout.rulers_dir}/RULERS_STATE.json"] if file_identity(state_path) != workspace_before else []),"next_action":"complete-workspace-adoption"}
    completion = {"name":plan["name"],"migration_digest":plan["digest"],"retire_domains":plan["retire_domains"],"workspace_inputs":plan["workspace_inputs"]}
    adoption = sync_plan(project_root=layout.project_root,rulers_dir=layout.rulers_dir,names=[plan["name"]],completion=completion)
    result = apply_sync(adoption,reviewed_by=reviewed_by,evidence=evidence)
    return {**result,"changed_files":sorted(set(changed_files+result["changed_files"])),"stage":"complete","source_next_action":"review-profile-and-activate-domains-for-independent-use"}


def read_json_from_bytes(content):
    import json
    return json.loads(content.decode("utf-8"))
