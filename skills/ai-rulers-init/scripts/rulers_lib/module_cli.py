"""Public module workflow CLI adapter."""
import json
from pathlib import Path

from .module_contracts import write_plan, read_json
from .module_registry import module_status, registration_plan, apply_registration


def add_module_commands(subparsers):
    for name in ("modules", "module-plan"):
        parser = subparsers.add_parser(name)
        parser.add_argument("--project-root", default=".")
        parser.add_argument("--rulers-dir", default="documents/rulers")
        if name == "module-plan":
            parser.add_argument("--operation", choices=("register", "sync", "adjust"), required=True)
            parser.add_argument("--module", action="append", default=[], dest="modules")
            parser.add_argument("--source-rulers", default="documents/rulers")
            parser.add_argument("--manifest", default="MODULE_EXPORT.json")
            parser.add_argument("--adjustments")
            parser.add_argument("--output", required=True)
    parser = subparsers.add_parser("module-export")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--rulers-dir", default="documents/rulers")
    parser.add_argument("--manifest", default="MODULE_EXPORT.json")
    parser.add_argument("--output", required=True)
    parser = subparsers.add_parser("module-migrate-plan")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--rulers-dir", default="documents/rulers")
    parser.add_argument("--module", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--retire-domain", action="append", default=[])
    parser.add_argument("--output", required=True)
    parser = subparsers.add_parser("module-migrate-apply")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--stage", choices=("source","complete"), default="complete")
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--reviewed-at")
    parser = subparsers.add_parser("module-apply")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--reviewed-by", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--reviewed-at")


def dispatch_module_command(args, *, skill_root):
    if args.command == "module-migrate-plan":
        from .module_migration import migration_plan
        root = Path(args.project_root).resolve()
        result = migration_plan(skill_root=skill_root,project_root=root,rulers_dir=args.rulers_dir,name=args.module,
            candidate_dir=args.candidate_dir,retire_domains=args.retire_domain)
        write_plan(Path(args.output),result,root=root)
        result = {"operation":"migrate","module":args.module,"digest":result["digest"],"plan_path":args.output,"retire_domains":args.retire_domain}
    elif args.command == "module-migrate-apply":
        from .module_migration import apply_migration
        result = apply_migration(read_json(Path(args.plan)),skill_root=skill_root,reviewed_by=args.reviewed_by,evidence=args.evidence,stage=args.stage)
    elif args.command == "module-export":
        from .module_exports import capture_export
        root = Path(args.project_root).resolve()
        result = capture_export(project_root=root, rulers_dir=args.rulers_dir, manifest=args.manifest)
        write_plan(Path(args.output), result, root=root)
        result = {"content_id": result["content_id"], "capture_id": result["capture_id"], "output": args.output}
    elif args.command == "modules":
        result = module_status(project_root=Path(args.project_root).resolve(), rulers_dir=args.rulers_dir)
    elif args.command == "module-plan":
        if args.operation == "register":
            result = registration_plan(project_root=Path(args.project_root).resolve(), rulers_dir=args.rulers_dir,
                names=args.modules, source_rulers=args.source_rulers, manifest=args.manifest)
        else:
            from .module_sync import sync_plan
            result = sync_plan(project_root=Path(args.project_root).resolve(),rulers_dir=args.rulers_dir,names=args.modules,operation=args.operation,adjustments_path=args.adjustments)
        write_plan(Path(args.output), result, root=Path(result["project_root"]))
        result = {"operation": result["operation"], "modules": result["names"], "plan_path": args.output, "digest": result["digest"], "requires_review": result.get("requires_review",True), "conflicts": result.get("conflicts",[])}
    else:
        plan = read_json(Path(args.plan))
        if plan["operation"] == "register":
            result = apply_registration(plan, reviewed_by=args.reviewed_by, evidence=args.evidence)
        else:
            from .module_sync import apply_sync
            result = apply_sync(plan,reviewed_by=args.reviewed_by,evidence=args.evidence)
    print(json.dumps(result, ensure_ascii=False))
