#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from rulers_lib.migration import migrate_v1
from rulers_lib.domain_lifecycle import (
    activate_domain,
    register_domain_candidate,
    render_domain_candidate,
)
from rulers_lib.paths import resolve_layout
from rulers_lib.plans import create_plan as create_unified_plan, plan_summary
from rulers_lib.apply import apply_plan_unified
from rulers_lib.state import (
    file_sha256,
    mark_runtime_ready,
    read_state,
    review_profile,
    state_json,
    transition_state,
)
from rulers_lib.validation import validate_project


SKILL_ROOT = Path(__file__).resolve().parents[1]


def _write_or_print(payload: dict, output: str | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and maintain AI rulers.")
    from rulers_lib.version import RELEASE_VERSION
    parser.add_argument("--version", action="version", version="ai-rulers-init " + RELEASE_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--project-root", default=".")
    plan_parser.add_argument("--rulers-dir", default="documents/rulers")
    plan_parser.add_argument("--policy")
    plan_parser.add_argument("--operation", default="auto", choices=("auto", "fresh", "resume", "reconcile", "upgrade", "repair", "noop"))
    plan_parser.add_argument("--resolution", action="append", default=[])
    plan_parser.add_argument("--candidate-profile")
    plan_parser.add_argument("--changed-path", action="append", default=[], dest="changed_paths")
    plan_parser.add_argument("--retired-domain", action="append", default=[], dest="retired_domains")
    plan_parser.add_argument("--output")

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--project-root")
    apply_parser.add_argument("--plan", required=True)
    apply_parser.add_argument("--reviewed-by")
    apply_parser.add_argument("--evidence")
    apply_parser.add_argument("--reviewed-at")

    migration_parser = subparsers.add_parser("migrate-v1")
    migration_parser.add_argument("--project-root", default=".")
    migration_parser.add_argument("--rulers-dir", default="documents/rulers")
    migration_parser.add_argument("--policy", default="strict-cn")
    migration_parser.add_argument("--apply", action="store_true")

    review_parser = subparsers.add_parser("review-profile")
    review_parser.add_argument("--project-root", default=".")
    review_parser.add_argument("--rulers-dir", default="documents/rulers")
    review_parser.add_argument("--reviewed-by", required=True)
    review_parser.add_argument("--evidence", required=True)
    review_parser.add_argument("--reviewed-at")

    ready_parser = subparsers.add_parser("mark-runtime-ready")
    ready_parser.add_argument("--project-root", default=".")
    ready_parser.add_argument("--rulers-dir", default="documents/rulers")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--project-root", default=".")
    status_parser.add_argument("--rulers-dir", default="documents/rulers")

    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument("--project-root", default=".")
    resume_parser.add_argument("--rulers-dir", default="documents/rulers")

    render_domain_parser = subparsers.add_parser("render-domain-candidate")
    render_domain_parser.add_argument("--project-root", default=".")
    render_domain_parser.add_argument("--rulers-dir", default="documents/rulers")
    render_domain_parser.add_argument("--domain", required=True)

    register_domain_parser = subparsers.add_parser("register-domain-candidate")
    register_domain_parser.add_argument("--project-root", default=".")
    register_domain_parser.add_argument("--rulers-dir", default="documents/rulers")
    register_domain_parser.add_argument("--domain", required=True)

    activate_domain_parser = subparsers.add_parser("activate-domain")
    activate_domain_parser.add_argument("--project-root", default=".")
    activate_domain_parser.add_argument("--rulers-dir", default="documents/rulers")
    activate_domain_parser.add_argument("--domain", required=True)
    activate_domain_parser.add_argument("--reviewed-by", required=True)
    activate_domain_parser.add_argument("--evidence", required=True)
    activate_domain_parser.add_argument("--reviewed-at")

    rules_plan_parser = subparsers.add_parser("rules-plan")
    rules_plan_parser.add_argument("--project-root", default=".")
    rules_plan_parser.add_argument("--rulers-dir", default="documents/rulers")
    rules_plan_parser.add_argument("--domain", required=True)
    rules_plan_parser.add_argument("--candidate-dir", required=True)
    rules_plan_parser.add_argument("--reason", required=True)
    rules_plan_parser.add_argument("--output", required=True)
    rules_apply_parser = subparsers.add_parser("rules-apply")
    rules_apply_parser.add_argument("--plan", required=True)
    rules_apply_parser.add_argument("--reviewed-by", required=True)
    rules_apply_parser.add_argument("--evidence", required=True)
    from rulers_lib.module_cli import add_module_commands, dispatch_module_command
    add_module_commands(subparsers)
    from rulers_lib.initialization import add_initialization_commands, dispatch_initialization
    add_initialization_commands(subparsers)
    args = parser.parse_args()
    try:
        if args.command in {"init-plan", "init-apply"}:
            print(json.dumps(dispatch_initialization(args, skill_root=SKILL_ROOT), ensure_ascii=False))
        elif args.command in {"modules", "module-plan", "module-apply", "module-export", "module-migrate-plan", "module-migrate-apply"}:
            dispatch_module_command(args, skill_root=SKILL_ROOT)
        elif args.command == "plan":
            from rulers_lib.plans import write_plan_bundle
            from rulers_lib.paths import resolve_safe_child
            project = Path(args.project_root).resolve()
            recorded_path = project / args.rulers_dir / "RULERS_STATE.json"
            if args.policy and recorded_path.is_file() and args.operation != "upgrade":
                recorded = read_state(recorded_path).get("policy", {}).get("id")
                if args.policy != recorded:
                    raise ValueError("Policy switch requires explicit --operation upgrade")
            payload = create_unified_plan(
                skill_root=SKILL_ROOT, project_root=project, rulers_dir=args.rulers_dir,
                policy_id=args.policy, operation=args.operation,
                candidate_profile=Path(args.candidate_profile) if args.candidate_profile else None,
                changed_paths=args.changed_paths, retired_domains=args.retired_domains,
                repair_resolutions=dict(item.split("=", 1) for item in args.resolution),
            )
            canonical = project / args.rulers_dir / ".plans" / payload["plan_id"] / "plan.json"
            output = canonical
            if args.output and payload["operation"] != "noop":
                requested = Path(args.output)
                relative = requested.resolve().relative_to(project) if requested.is_absolute() else requested
                output = resolve_safe_child(project, relative)
                if (project / args.rulers_dir) in output.parents:
                    raise ValueError("Use the canonical plan_path or an output outside installed rulers")
                if output.suffix != ".json" or output.exists():
                    raise ValueError("Plan output must be a new JSON file")
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open("xb") as stream:
                    stream.write(canonical.read_bytes())
                if payload["detail_references"]:
                    patch = output.parent / "profile.patch"
                    if patch.exists():
                        raise ValueError("Plan detail conflict; use a new output directory")
                    patch.write_bytes((canonical.parent / "profile.patch").read_bytes())
            print(json.dumps(plan_summary(payload, output if payload["operation"] != "noop" else None), ensure_ascii=False))
        elif args.command == "apply":
            raw = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            project = Path(args.project_root or raw["project_root"]).resolve()
            print(json.dumps(apply_plan_unified(
                Path(args.plan).resolve(), skill_root=SKILL_ROOT, project_root=project,
                reviewed_by=args.reviewed_by, evidence=args.evidence, reviewed_at=args.reviewed_at,
            ), ensure_ascii=False))
        elif args.command == "rules-plan":
            from rulers_lib.rule_maintenance import plan_rules_change
            from rulers_lib.paths import resolve_safe_child
            project = Path(args.project_root).resolve()
            plan = plan_rules_change(skill_root=SKILL_ROOT, project_root=project, rulers_dir=args.rulers_dir,
                domain=args.domain, candidate_dir=args.candidate_dir, reason=args.reason)
            output = Path(args.output)
            output = resolve_safe_child(project, output.resolve().relative_to(project) if output.is_absolute() else output)
            if output.exists() or (project / args.rulers_dir) in output.parents:
                raise ValueError("Use a new plan path outside installed rulers")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({key:plan[key] for key in ("added", "deleted", "modified", "reason", "sha256")}, ensure_ascii=False))
        elif args.command == "rules-apply":
            from rulers_lib.rule_maintenance import apply_rules_change
            print(json.dumps(apply_rules_change(plan=json.loads(Path(args.plan).read_text(encoding="utf-8")),
                skill_root=SKILL_ROOT, reviewed_by=args.reviewed_by, evidence=args.evidence), ensure_ascii=False))
        elif args.command == "migrate-v1":
            payload = migrate_v1(
                skill_root=SKILL_ROOT,
                project_root=Path(args.project_root),
                rulers_dir=args.rulers_dir,
                policy_id=args.policy,
                apply=args.apply,
            )
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        elif args.command == "review-profile":
            layout = resolve_layout(Path(args.project_root), args.rulers_dir)
            from rulers_lib.mutations import mutation, write_text
            with mutation(layout):
                state_path = layout.rulers_root / "RULERS_STATE.json"
                state = read_state(state_path)
                profile_path = layout.rulers_root / "PROJECT_PROFILE.md"
                from rulers_lib.reconcile import parse_profile
                from rulers_lib.domains import load_domain_registry
                parse_profile(profile_path.read_text(encoding="utf-8"), allowed_scopes=set(load_domain_registry(SKILL_ROOT)))
                profile_hash = file_sha256(profile_path)
                reviewed = review_profile(
                    state,
                    reviewed_by=args.reviewed_by,
                    reviewed_at=args.reviewed_at
                    or datetime.now(timezone.utc).astimezone().isoformat(),
                    evidence=args.evidence,
                    content_sha256=profile_hash,
                )
                profile_relative = str(profile_path.relative_to(layout.project_root))
                profile_inventory = reviewed.setdefault("managed_files", {}).setdefault(
                    profile_relative,
                    {"template_id": "PROJECT_PROFILE.md", "source_sha256": profile_hash},
                )
                profile_inventory["rendered_sha256"] = profile_hash
                profile_inventory["ownership"] = "collaborative"
                write_text(state_path, state_json(reviewed))
                print(json.dumps({"phase": reviewed["phase"]}, ensure_ascii=False))
        elif args.command == "mark-runtime-ready":
            layout = resolve_layout(Path(args.project_root), args.rulers_dir)
            from rulers_lib.mutations import mutation, write_text
            with mutation(layout):
                state_path = layout.rulers_root / "RULERS_STATE.json"
                state = read_state(state_path)
                issues = validate_project(
                    mode="candidate",
                    project_root=layout.project_root,
                    rulers_dir=layout.rulers_dir,
                )
                errors = [issue for issue in issues if issue.severity == "error"]
                if errors:
                    raise ValueError(
                        "Candidate validation failed: "
                        + "; ".join(f"{issue.code} {issue.message}" for issue in errors)
                    )
                ready = mark_runtime_ready(state)
                write_text(state_path, state_json(ready))
                print(json.dumps({"phase": ready["phase"]}, ensure_ascii=False))
        elif args.command in {"status", "resume"}:
            layout = resolve_layout(Path(args.project_root), args.rulers_dir)
            state_path = layout.rulers_root / "RULERS_STATE.json"
            if state_path.is_file():
                state = read_state(state_path)
                phase = state.get("phase")
                next_actions = {
                    "planned": "apply-plan",
                    "profile_draft": "review-profile",
                    "profile_reviewed": "generate-rules",
                    "rules_candidate": "review-and-activate",
                    "runtime_ready": "none",


                    "repair_required": "repair",
                }
                payload = {
                    "mode": "managed",
                    "phase": phase,
                    "next_action": next_actions.get(phase, "repair"),
                }
                issues = validate_project(
                    mode="candidate",
                    project_root=layout.project_root,
                    rulers_dir=layout.rulers_dir,
                )
                errors = [issue for issue in issues if issue.severity == "error"]
                if errors:
                    payload["phase"] = "repair_required"
                    payload["next_action"] = "repair"
                    payload["issues"] = sorted({issue.code for issue in errors})
            elif (layout.rulers_root / "PROJECT_PROFILE.md").is_file():
                payload = {
                    "mode": "legacy-migration",
                    "phase": "legacy",
                    "next_action": "migrate-v1",
                }
            else:
                payload = {
                    "mode": "fresh",
                    "phase": "uninitialized",
                    "next_action": "plan",
                }
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        elif args.command == "render-domain-candidate":
            payload = render_domain_candidate(
                skill_root=SKILL_ROOT,
                project_root=Path(args.project_root),
                rulers_dir=args.rulers_dir,
                domain=args.domain,
            )
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        elif args.command == "register-domain-candidate":
            payload = register_domain_candidate(
                skill_root=SKILL_ROOT,
                project_root=Path(args.project_root),
                rulers_dir=args.rulers_dir,
                domain=args.domain,
            )
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        elif args.command == "activate-domain":
            payload = activate_domain(
                skill_root=SKILL_ROOT,
                project_root=Path(args.project_root),
                rulers_dir=args.rulers_dir,
                domain=args.domain,
                reviewed_by=args.reviewed_by,
                evidence=args.evidence,
                reviewed_at=args.reviewed_at,
            )
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
