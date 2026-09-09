#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rulers_lib.validation import (
    build_runtime_context,
    inspect_project,
    runtime_context_json,
    validate_project,
    validate_template,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ai-rulers templates or runtime files.")
    parser.add_argument("--mode", choices=("template", "candidate", "runtime", "context", "load"), required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--rulers-dir", default="documents/rulers")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--domain", action="append", default=[], dest="domains")
    parser.add_argument("--rule", action="append", default=[])
    parser.add_argument("--module", action="append", default=[], dest="modules")
    parser.add_argument("--workspace-domain", action="append", default=[])
    parser.add_argument("--workspace-rule", action="append", default=[])
    args = parser.parse_args()
    if (args.workspace_domain or args.workspace_rule) and not args.modules:
        parser.error("Workspace selectors require --module; use --domain/--rule for standalone projects")

    if args.mode == "template":
        skill_root = Path(__file__).resolve().parents[1]
        issues = validate_template(skill_root)
    elif args.mode in {"context", "load"}:
        try:
            inspection = inspect_project(
                project_root=Path(args.project_root),
                rulers_dir=args.rulers_dir,
            )
            if args.mode == "load":
                from rulers_lib.rule_loading import build_load_bundle
                if args.modules:
                    from rulers_lib.module_loading import module_bundle
                    bundle = module_bundle(inspection,names=args.modules,domains=args.domains,rules=args.rule,
                        workspace_domains=args.workspace_domain,workspace_rules=args.workspace_rule)
                else:
                    bundle = build_load_bundle(inspection, domains=args.domains, rules=args.rule)
                if not bundle["within_budget"]:
                    raise ValueError("Selected rules exceed load budget; narrow domain/rule selection")
                print(bundle["content"] if args.format == "text" else json.dumps({k:v for k,v in bundle.items() if k != "content"}, ensure_ascii=False))
                return 0
            if args.modules or (inspection.state or {}).get("modules"):
                from rulers_lib.module_loading import module_context
                context = module_context(inspection,names=args.modules,domains=args.domains,workspace_domains=args.workspace_domain)
            else:
                context = build_runtime_context(inspection,requested_domains=args.domains)
            output = runtime_context_json(context)
            sys.stdout.buffer.write(output + b"\n")
            return 0
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    else:
        issues = validate_project(
            mode=args.mode,
            project_root=Path(args.project_root),
            rulers_dir=args.rulers_dir,
        )

    if args.format == "json":
        print(json.dumps({"mode": args.mode, "issues": [issue.to_dict() for issue in issues]}, ensure_ascii=False, indent=2))
    elif issues:
        print(f"Rulers {args.mode} validation failed:")
        for issue in issues:
            print(f"- [{issue.code}] {issue.message}" + (f" ({issue.path})" if issue.path else ""))
    else:
        print(f"Rulers {args.mode} validation passed.")
    return 1 if any(issue.severity == "error" for issue in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
