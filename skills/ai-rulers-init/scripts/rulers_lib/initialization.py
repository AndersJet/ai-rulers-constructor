"""Default initialization discovery, shared by preparation and reviewed application."""

from pathlib import Path

from .module_contracts import (
    checked_path,
    read_json,
    identity,
    write_plan,
    engine_identity,
)
from .module_git import discover_modules
from .paths import resolve_layout

INITIALIZATION_PLAN_SCHEMA_VERSION = 1


def choose_rulers_dir(root, explicit=None):
    if explicit is not None:
        return explicit
    import re
    from .root_entry import find_managed_blocks

    for name in ("AGENTS.md", "CLAUDE.md"):
        entry = root / name
        if entry.is_symlink():
            raise ValueError("Project entry must not be a symlink")
        if entry.is_file():
            blocks = find_managed_blocks(entry.read_text(encoding="utf-8"))
            if len(blocks) == 1:
                match = re.search(r"`([^`\n]+)/AGENTS\.md`", blocks[0].group())
                if match:
                    return match[1]
    return "documents/rulers"


def discover_initialization(*, project_root, rulers_dir=None, excluded=None):
    root = Path(project_root).resolve()
    from .initialization_gitignore import check_gitignore_path

    check_gitignore_path(root)
    layout = resolve_layout(root, choose_rulers_dir(root, rulers_dir))
    from .initialization_projection import SKIP

    if set(Path(layout.rulers_dir).parts) & SKIP:
        raise ValueError(
            "Rules directory conflicts with initialization scratch or dependency directories"
        )
    state_path = layout.rulers_root / "RULERS_STATE.json"
    state = read_json(state_path) if state_path.is_file() else {}
    previous_exclusions = state.get("initialization", {}).get("excluded_modules", [])
    inherited = excluded is None
    excluded = sorted(set(previous_exclusions if inherited else excluded))
    topology = (
        discover_modules(layout.project_root)
        if (layout.project_root / ".gitmodules").exists()
        else {"gitmodules_hash": None, "modules": []}
    )
    names = {m["name"] for m in topology["modules"]}
    if not inherited and set(excluded) - names:
        raise ValueError("Excluded module is not a discovered direct submodule")
    excluded = sorted(set(excluded) & names)
    root_scope = "workspace"
    while root_scope in names:
        root_scope = "_" + root_scope
    modules = {}
    for module in topology["modules"]:
        name = module["name"]
        record = state.get("modules", {}).get(name, {})
        source_dir = record.get("source", {}).get("rulers_dir") or (
            choose_rulers_dir(layout.project_root / module["path"])
            if module["initialized"] and name not in excluded
            else "documents/rulers"
        )
        manifest = record.get("source", {}).get("manifest", "MODULE_EXPORT.json")
        source = checked_path(layout.project_root, module["path"])
        ready = False
        if module["initialized"] and name not in excluded:
            ready = (
                checked_path(source, source_dir) / "RULERS_STATE.json"
            ).is_file() and checked_path(source, source_dir + "/" + manifest).is_file()
        action = (
            "excluded"
            if name in excluded
            else "unavailable"
            if not module["initialized"]
            else "check-sync"
            if ready
            else "prepare-source"
        )
        modules[name] = {
            "git": module,
            "rulers_dir": source_dir,
            "manifest": manifest,
            "action": action,
        }
    return {
        "project_root": str(layout.project_root),
        "rulers_dir": layout.rulers_dir,
        "mode": "workspace" if modules else "single-project",
        "root_scope": root_scope,
        "topology": topology,
        "excluded_modules": excluded,
        "modules": modules,
        "missing_modules": sorted(set(state.get("modules", {})) - names),
        "root_action": "check-existing" if state else "prepare-profile",
    }


def add_initialization_commands(subparsers):
    parser = subparsers.add_parser(
        "init-plan",
        help="Discover the workspace and prepare one reviewed initialization plan",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--rulers-dir")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--exclude-module", action="append", default=None)
    selection.add_argument("--include-all-modules", action="store_true")
    parser.add_argument("--candidates")
    parser.add_argument("--policy")
    parser.add_argument("--output")
    parser = subparsers.add_parser("init-apply")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--reviewed-by", default="")
    parser.add_argument("--evidence", default="")


def dispatch_initialization(args, *, skill_root):
    if args.command == "init-apply":
        return apply_initialization(
            read_json(Path(args.plan)),
            skill_root=skill_root,
            reviewed_by=args.reviewed_by,
            evidence=args.evidence,
        )
    plan = build_review_plan(
        skill_root=skill_root,
        project_root=Path(args.project_root).resolve(),
        rulers_dir=args.rulers_dir,
        excluded=[] if args.include_all_modules else args.exclude_module,
        candidates=args.candidates,
        policy=args.policy,
    )
    output = args.output or ".rulers-work/init-" + plan["digest"][7:23] + ".json"
    destination = Path(output)
    relative = (
        destination.relative_to(plan["project_root"]).as_posix()
        if destination.is_absolute()
        else destination.as_posix()
    )
    if not relative.startswith(".rulers-work/") or destination.suffix != ".json":
        raise ValueError("Initialization plans belong under .rulers-work/")
    write_plan(destination, plan, root=Path(plan["project_root"]))
    from .initialization_review import review_markdown

    review_path = checked_path(
        Path(plan["project_root"]), relative.removesuffix(".json") + ".review.md"
    )
    review_text = review_markdown(plan)
    if review_path.exists() and review_path.read_text() != review_text:
        raise ValueError("Review output changed; choose a new output path")
    if not review_path.exists():
        review_path.write_text(review_text)
    return {
        "mode": plan["mode"],
        "status": plan["status"],
        "plan_path": output,
        "review_path": review_path.relative_to(plan["project_root"]).as_posix(),
        "modules": len(plan["modules"]),
        "root_scope": plan["root_scope"],
        "preparation": plan["preparation"][:6],
        "preparation_count": len(plan["preparation"]),
    }


def candidate_settings(root, candidates, policy):
    from .initialization_projection import files_under

    settings = (
        read_json(checked_path(root, candidates, required=True))
        if candidates
        else {"projects": {}}
    )
    if set(settings) - {"projects", "resolutions"} or not isinstance(
        settings.get("projects", {}), dict
    ):
        raise ValueError(
            "Candidates require projects mapping (workspace and module names)"
        )
    resolutions = settings.get("resolutions", [])
    if not isinstance(resolutions, list) or any(
        not isinstance(r, dict)
        or set(r) != {"module", "workspace_rule", "module_rule", "decision", "reason"}
        or r.get("decision") != "keep-scoped"
        or not all(isinstance(v, str) and v for v in r.values())
        for r in resolutions
    ):
        raise ValueError(
            "Ownership resolutions require module, workspace_rule, module_rule, keep-scoped decision and reason"
        )
    inputs = {candidates} if candidates else set()
    for name, project in settings.get("projects", {}).items():
        if not isinstance(project, dict) or set(project) - {
            "profile",
            "domains",
            "export_manifest",
            "adjustments",
        }:
            raise ValueError("Unknown project candidate fields: " + name)
        domains = project.get("domains", {})
        if not isinstance(domains, dict):
            raise ValueError("Candidate domains must map names to directories")
        refs = [
            project[k]
            for k in ("profile", "export_manifest", "adjustments")
            if k in project
        ] + list(domains.values())
        if project.get("adjustments"):
            adjustment = read_json(
                checked_path(root, project["adjustments"], required=True)
            )
            from .module_adjustments import validate_adjustment_definition

            validate_adjustment_definition(adjustment)
            refs += list(adjustment.get("replace", {}).values()) + [
                v["path"] for v in adjustment.get("add", {}).values()
            ]
        for relative in refs:
            source = checked_path(root, relative)
            if source.is_file():
                inputs.add(relative)
            elif source.is_dir():
                if any(p.is_symlink() for p in source.rglob("*")):
                    raise ValueError("Candidate directories cannot contain symlinks")
                inputs.update(
                    p.relative_to(root).as_posix() for p in files_under(source)
                )
            else:
                raise ValueError("Candidate input missing: " + relative)
    settings["inputs"] = sorted(inputs)
    settings["policy"] = policy
    return settings


def input_scopes(root, discovery):
    from .initialization_projection import snapshot

    excluded = [m["git"]["path"] for m in discovery["modules"].values()]
    scopes = {
        discovery["root_scope"]: {
            "path": "",
            "rulers_dir": discovery["rulers_dir"],
            "inputs": snapshot(root, excluded),
        }
    }
    for name, module in discovery["modules"].items():
        if module["action"] not in ("excluded", "unavailable"):
            scopes[name] = {
                "path": module["git"]["path"],
                "rulers_dir": module["rulers_dir"],
                "inputs": snapshot(root / module["git"]["path"]),
            }
    return scopes


def stable_topology(discovery):
    return [
        {k: v for k, v in m["git"].items() if k != "dirty"}
        for m in discovery["modules"].values()
    ]


def encode_changes(changes):
    import base64

    return {
        name: {
            **scope,
            "files": {
                p: base64.b64encode(content).decode() if content is not None else None
                for p, content in scope["files"].items()
            },
        }
        for name, scope in changes.items()
    }


def build_review_plan(
    *, skill_root, project_root, rulers_dir, excluded, candidates, policy
):
    from .initialization_projection import project_batch
    from .module_contracts import file_identity

    root = Path(project_root).resolve()
    discovery = discover_initialization(
        project_root=root, rulers_dir=rulers_dir, excluded=excluded
    )
    settings = candidate_settings(root, candidates, policy)
    if set(settings.get("projects", {})) - {
        discovery["root_scope"],
        *discovery["modules"],
    }:
        raise ValueError("Candidate project is not in this workspace")
    scopes = input_scopes(root, discovery)
    inputs = {
        p: file_identity(checked_path(root, p, required=True))
        for p in settings["inputs"]
    }
    recipe = {
        **discovery,
        "initialization_plan_version": INITIALIZATION_PLAN_SCHEMA_VERSION,
        "engine_id": engine_identity(),
        "candidates": candidates,
        "policy": policy,
        "scopes": scopes,
        "candidate_inputs": inputs,
    }
    batch_id = identity(recipe)
    changes, pending = project_batch(
        skill_root=skill_root,
        root=root,
        discovery=discovery,
        settings=settings,
        review={
            "reviewed_by": "pending-review",
            "evidence": "pending-review",
            "reviewed_at": "1970-01-01T00:00:00+00:00",
        },
        batch_id=batch_id,
    )
    encoded = encode_changes(changes)
    plan = {
        **recipe,
        "batch_id": batch_id,
        "changes": encoded,
        "preparation": pending,
        "status": "review"
        if changes
        else "preparation"
        if any(p.get("kind") != "unavailable" for p in pending)
        else "noop",
    }
    plan["digest"] = identity(plan)
    return plan


def apply_initialization(plan, *, skill_root, reviewed_by="", evidence=""):
    import base64
    from datetime import datetime, timezone
    from .module_contracts import require_protocol, file_identity
    from .initialization_projection import snapshot
    from .initialization_materialization import approved_changes, verify_execution
    from .mutations import mutation
    from .transactions import ReplaceAction, DeleteAction

    require_protocol(
        plan, "initialization_plan_version", INITIALIZATION_PLAN_SCHEMA_VERSION
    )
    if plan.get("digest") != identity({k: v for k, v in plan.items() if k != "digest"}):
        raise ValueError("Initialization plan digest mismatch")
    if plan["engine_id"] != engine_identity():
        raise ValueError("Initialization implementation changed; replan")
    root = Path(plan["project_root"])
    current = discover_initialization(
        project_root=root,
        rulers_dir=plan["rulers_dir"],
        excluded=plan["excluded_modules"],
    )
    if stable_topology(current) != stable_topology(plan):
        raise ValueError("Module topology changed; replan")
    if plan["status"] == "preparation":
        raise ValueError("Prepare the listed candidates before applying")
    if plan["status"] != "noop" and (not reviewed_by.strip() or not evidence.strip()):
        raise ValueError(
            "Initialization requires reviewer and evidence for the consolidated changes"
        )
    execution_path = checked_path(
        root, ".rulers-work/init-" + plan["digest"][7:23] + ".execution.json"
    )
    if execution_path.exists():
        execution = read_json(execution_path)
        if (
            execution.get("digest")
            != identity({k: v for k, v in execution.items() if k != "digest"})
            or execution["plan_digest"] != plan["digest"]
        ):
            raise ValueError("Initialization execution record is invalid")
    else:
        fresh = build_review_plan(
            skill_root=skill_root,
            project_root=root,
            rulers_dir=plan["rulers_dir"],
            excluded=plan["excluded_modules"],
            candidates=plan["candidates"],
            policy=plan["policy"],
        )
        if fresh != plan:
            raise ValueError("Initialization inputs changed; replan")
        if plan["status"] == "noop":
            return {
                "operation": "noop",
                "changed_files": [],
                "preparation": plan["preparation"],
            }
        review = {
            "reviewed_by": reviewed_by,
            "evidence": evidence,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        execution = {
            "plan_digest": plan["digest"],
            "review": review,
            "changes": approved_changes(plan, review),
            "preparation": plan["preparation"],
        }
        execution["digest"] = identity(execution)
        write_plan(execution_path, execution, root=root)
    verify_execution(plan, execution, reviewed_by, evidence)
    for path, digest in plan["candidate_inputs"].items():
        if file_identity(checked_path(root, path, required=True)) != digest:
            raise ValueError(
                "Candidate changed; replan without overwriting completed work"
            )
    from .initialization_execution import verify_scopes, execution_scope

    verify_scopes(plan, execution, root, recover=True)
    changed = []
    for name in sorted(
        execution["changes"], key=lambda n: (n == plan["root_scope"], n)
    ):
        scope = execution["changes"][name]
        project = checked_path(root, scope["path"]) if scope["path"] else root
        layout = resolve_layout(project, scope["rulers_dir"])
        txn_id = identity({"plan": plan["digest"], "scope": name})[7:23]
        verify_scopes(plan, execution, root)
        before, after = execution_scope(plan, name, scope)
        excluded = (
            [m["git"]["path"] for m in plan["modules"].values()]
            if name == plan["root_scope"]
            else []
        )
        actual = snapshot(project, excluded)
        if actual == after:
            continue
        if actual != before:
            raise ValueError(
                "Project inputs changed: " + name + "; preserve work and replan"
            )
        with mutation(layout, transaction_id=txn_id) as transaction:
            if snapshot(project, excluded) != before:
                raise ValueError("Project changed before initialization write")
            actions = [
                DeleteAction(path)
                if value is None
                else ReplaceAction(path, base64.b64decode(value, validate=True))
                for path, value in scope["files"].items()
            ]
            changed.extend(
                str(Path(scope["path"]) / p) for p in transaction.apply(actions)
            )
    return {
        "operation": "apply" if changed else "noop",
        "changed_files": changed,
        "preparation": execution["preparation"],
    }
