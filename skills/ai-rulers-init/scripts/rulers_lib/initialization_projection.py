"""Rehearse existing lifecycle operations in an isolated copy before approval."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .module_contracts import checked_path, file_identity, read_json, json_bytes
from .module_registry import registration_plan
from .module_sync import sync_plan, apply_sync
from .state import state_json

SKIP = {
    ".git",
    ".codegraph",
    "node_modules",
    ".venv",
    "__pycache__",
    ".plans",
    ".transactions",
    ".rulers-work",
}
REVIEWER = "__initialization_candidate_review__"


def files_under(root, excluded=()):
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in SKIP
            and not (Path(folder) / d).is_symlink()
            and (Path(folder) / d).relative_to(root).as_posix() not in excluded
        )
        for name in sorted(files):
            path = Path(folder) / name
            if not path.is_symlink():
                yield path


def snapshot(root, excluded=()):
    return {
        p.relative_to(root).as_posix(): file_identity(p)
        for p in files_under(root, excluded)
    }


def copy_inputs(source, destination, excluded=()):
    for path in files_under(source, excluded):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def output_files(root, rulers_dir):
    result = {}
    directory = checked_path(root, rulers_dir)
    if directory.exists():
        for path in files_under(directory):
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in ("AGENTS.md", "CLAUDE.md", "CHANGELOG.md", ".gitignore"):
        path = root / name
        if path.is_file():
            result[name] = path.read_bytes()
    return result


def _cli(skill_root, root, rulers_dir, *args):
    result = subprocess.run(
        [sys.executable, str(skill_root / "scripts/rulers_init.py"), *map(str, args)],
        cwd=root,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def stamp(state, review, batch_id):
    def visit(value):
        if isinstance(value, dict):
            if value.get("reviewed_by") == REVIEWER:
                value.update(review)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(state)
    state["last_operation"] = {
        "kind": "initialization",
        "status": "complete",
        "batch_id": batch_id,
    }
    return state


def local_candidates(preview, project, settings):
    local = dict(settings)
    for field in ("profile", "export_manifest"):
        if settings.get(field):
            source = checked_path(preview, settings[field], required=True)
            relative = ".rulers-work/init-inputs/" + field + source.suffix
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source != target:
                shutil.copyfile(source, target)
            local[field] = relative
    local["domains"] = {}
    for domain, path in settings.get("domains", {}).items():
        relative = ".rulers-work/init-inputs/domains/" + domain
        target = checked_path(project, relative)
        source = checked_path(preview, path)
        if source != target:
            copy_inputs(source, target)
        local["domains"][domain] = relative
    return local


def prepare_project(
    skill_root,
    root,
    rulers_dir,
    settings,
    policy,
    review,
    batch_id,
    manifest_name="MODULE_EXPORT.json",
):
    state_path = root / rulers_dir / "RULERS_STATE.json"
    before = state_path.read_bytes() if state_path.exists() else None
    target = ["--project-root", str(root), "--rulers-dir", rulers_dir]
    options = []
    if not state_path.exists() and policy is None:
        policy = "project-native"
    if policy:
        options += ["--policy", policy]
    if settings.get("profile"):
        options += ["--candidate-profile", settings["profile"]]
    plan = _cli(skill_root, root, rulers_dir, "plan", *target, *options)
    if plan["operation"] != "noop":
        _cli(
            skill_root,
            root,
            rulers_dir,
            "apply",
            "--plan",
            root / plan["plan_path"],
            "--reviewed-by",
            REVIEWER,
            "--evidence",
            batch_id,
        )
    state = read_json(state_path)
    if state["profile"]["status"] != "reviewed":
        if not settings.get("profile"):
            raise ValueError(
                "Prepare an evidence-backed profile candidate before approval"
            )
        _cli(
            skill_root,
            root,
            rulers_dir,
            "review-profile",
            *target,
            "--reviewed-by",
            REVIEWER,
            "--evidence",
            batch_id,
        )
    from .domains import load_domain_registry

    registry = load_domain_registry(skill_root)
    ordered = []

    def include(domain):
        if domain in ordered:
            return
        for dependency in registry[domain].get("requires_active", []):
            if dependency in settings.get("domains", {}):
                include(dependency)
        ordered.append(domain)

    for domain in settings.get("domains", {}):
        include(domain)
    for domain in ordered:
        candidate = settings["domains"][domain]
        from .rule_maintenance import plan_rules_change, apply_rules_change
        from .domain_lifecycle import activate_domain

        plan = plan_rules_change(
            skill_root=skill_root,
            project_root=root,
            rulers_dir=rulers_dir,
            domain=domain,
            candidate_dir=candidate,
            reason="Reviewed initialization candidate",
        )
        changed = apply_rules_change(
            plan=plan, skill_root=skill_root, reviewed_by=REVIEWER, evidence=batch_id
        )
        state = read_json(state_path)
        if (
            changed["changed_files"]
            or state["domains"][domain].get("review_status") != "reviewed"
        ):
            activate_domain(
                skill_root=skill_root,
                project_root=root,
                rulers_dir=rulers_dir,
                domain=domain,
                reviewed_by=REVIEWER,
                evidence=batch_id,
            )
    state = read_json(state_path)
    if state["phase"] != "runtime_ready":
        _cli(skill_root, root, rulers_dir, "mark-runtime-ready", *target)
    if settings.get("export_manifest"):
        path = checked_path(root, settings["export_manifest"], required=True)
        checked_path(root, rulers_dir + "/" + manifest_name).write_bytes(
            path.read_bytes()
        )
    if state_path.read_bytes() != before:
        state_path.write_text(
            state_json(stamp(read_json(state_path), review, batch_id))
        )


def project_changes(before, after):
    return {
        path: after.get(path)
        for path in sorted(before.keys() | after.keys())
        if before.get(path) != after.get(path)
    }


def project_batch(*, skill_root, root, discovery, settings, review, batch_id):
    """Return reviewed target bytes. Only this temporary tree is changed."""
    with tempfile.TemporaryDirectory(prefix="rulers-init-preview-") as td:
        preview = Path(td).resolve()
        copy_inputs(
            root, preview, [m["git"]["path"] for m in discovery["modules"].values()]
        )
        for m in discovery["modules"].values():
            if m["action"] not in ("excluded", "unavailable"):
                copy_inputs(root / m["git"]["path"], preview / m["git"]["path"])
        # Candidate inputs live outside installed rules and may be under .rulers-work.
        for path in settings.get("inputs", []):
            source = checked_path(root, path, required=True)
            target = preview / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        root_scope = discovery["root_scope"]
        scopes = {root_scope: {"path": "", "rulers_dir": discovery["rulers_dir"]}}
        scopes.update(
            {
                name: {"path": m["git"]["path"], "rulers_dir": m["rulers_dir"]}
                for name, m in discovery["modules"].items()
                if m["action"] not in ("excluded", "unavailable")
            }
        )
        before = {
            name: output_files(preview / s["path"], s["rulers_dir"])
            for name, s in scopes.items()
        }
        pending = [
            {
                "scope": n,
                "kind": "unavailable",
                "reason": "Module not initialized; registration only, no Git operation",
            }
            for n, m in discovery["modules"].items()
            if m["action"] == "unavailable"
        ]
        eligible = []
        changes = {}
        for name, scope in scopes.items():
            project = preview / scope["path"]
            candidate = settings.get("projects", {}).get(name, {})
            try:
                from .transactions import inspect_incomplete_transaction
                from .paths import resolve_layout

                if inspect_incomplete_transaction(
                    resolve_layout(root / scope["path"], scope["rulers_dir"])
                ):
                    raise ValueError(
                        "Recover the existing project transaction before initialization"
                    )
                prepare_project(
                    skill_root,
                    project,
                    scope["rulers_dir"],
                    local_candidates(preview, project, candidate),
                    settings.get("policy") if name == root_scope else None,
                    review,
                    batch_id,
                    discovery["modules"]
                    .get(name, {})
                    .get("manifest", "MODULE_EXPORT.json"),
                )
                if name != root_scope:
                    eligible.append(name)
            except (ValueError, KeyError, RuntimeError) as exc:
                pending.append(
                    {
                        "scope": name,
                        "reason": str(exc).replace(str(preview), "<workspace>"),
                    }
                )
                # A failed rehearsal must not leak partial changes into the review.
                for relative in output_files(project, scope["rulers_dir"]):
                    if relative not in before[name]:
                        (project / relative).unlink()
                for path, content in before[name].items():
                    target = project / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
        if any(p["scope"] == root_scope for p in pending):
            return {}, pending
        state_path = preview / discovery["rulers_dir"] / "RULERS_STATE.json"
        state = read_json(state_path)
        for name, m in discovery["modules"].items():
            if m["action"] == "excluded":
                continue
            reg = registration_plan(
                project_root=preview,
                rulers_dir=discovery["rulers_dir"],
                names=[name],
                source_rulers=m["rulers_dir"],
                manifest=m["manifest"],
                _topology_root=root,
            )
            state.setdefault("modules", {}).update(reg["desired"])
        for name in discovery["missing_modules"]:
            state["modules"][name]["phase"] = "unavailable"
            pending.append(
                {
                    "scope": name,
                    "reason": "Registered submodule disappeared; retained snapshot pending explicit maintenance",
                }
            )
        state_path.write_text(state_json(state))
        accepted = state.get("initialization", {}).get("ownership_resolutions", {})
        accepted = dict(accepted)
        for name in eligible:
            try:
                plan = sync_plan(
                    project_root=preview,
                    rulers_dir=discovery["rulers_dir"],
                    names=[name],
                    adjustments_path=settings.get("projects", {})
                    .get(name, {})
                    .get("adjustments"),
                    _source_workspace=root,
                )
                from .initialization_ownership import overlaps

                ownership, decisions = overlaps(
                    preview,
                    discovery["rulers_dir"],
                    read_json(state_path),
                    name,
                    plan["captures"][name],
                    settings.get("resolutions", []),
                    accepted,
                )
                if ownership:
                    pending.extend({"scope": name, **item} for item in ownership)
                    root_delta = project_changes(
                        before[root_scope],
                        output_files(preview, discovery["rulers_dir"]),
                    )
                    if any(
                        discovery["rulers_dir"] + "/" + item["workspace_rule"]
                        in root_delta
                        for item in ownership
                    ):
                        return {}, pending
                    raise ValueError(
                        "ownership review required before changing source or adoption"
                    )
                accepted.update(decisions)
                if plan["conflicts"]:
                    raise ValueError(str(plan["conflicts"]))
                apply_sync(
                    plan,
                    reviewed_by=REVIEWER,
                    evidence=batch_id,
                    _source_workspace=root,
                )
            except (ValueError, KeyError, RuntimeError) as exc:
                pending.append(
                    {
                        "scope": name,
                        "reason": str(exc).replace(str(preview), "<workspace>"),
                    }
                )
                scope = scopes[name]
                project = preview / scope["path"]
                for relative in output_files(project, scope["rulers_dir"]):
                    if relative not in before[name]:
                        (project / relative).unlink()
                for relative, content in before[name].items():
                    (project / relative).parent.mkdir(parents=True, exist_ok=True)
                    (project / relative).write_bytes(content)
        state = read_json(state_path)
        config = {"excluded_modules": discovery["excluded_modules"]}
        if accepted:
            config["ownership_resolutions"] = accepted
        if (
            discovery["modules"]
            or discovery["missing_modules"]
            or state.get("initialization")
        ) and state.get("initialization") != config:
            state["initialization"] = config
        if json_bytes(state) != json_bytes(
            json.loads(
                before[root_scope].get(
                    discovery["rulers_dir"] + "/RULERS_STATE.json", b"{}"
                )
            )
        ):
            state = stamp(state, review, batch_id)
        state_path.write_text(state_json(state))
        from .initialization_gitignore import prepare_gitignore

        prepare_gitignore(preview)
        for name, scope in scopes.items():
            delta = project_changes(
                before[name], output_files(preview / scope["path"], scope["rulers_dir"])
            )
            if delta:
                changes[name] = {
                    "path": scope["path"],
                    "rulers_dir": scope["rulers_dir"],
                    "files": delta,
                }
        return changes, pending
