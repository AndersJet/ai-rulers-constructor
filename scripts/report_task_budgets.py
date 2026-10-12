"""Measure task leaves on adopted, template-derived isolated targets, not model quality."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

from scripts.runtime_fixture import SKILL_ROOT, runtime_fixture

sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from rulers_lib.rule_loading import build_load_bundle
from rulers_lib.validation import BUDGETS, build_runtime_context, inspect_project, runtime_context_json


TASKS = {
    "backend-fix": (("backend",), ("backend/TESTING.md",)),
    "authorization": (("backend", "security"), ("backend/API_SECURITY.md", "security/AUTHORIZATION.md")),
    "migration": (("database",), ("database/MIGRATION.md", "database/REVIEW_CHECKLIST.md")),
    "web-ui": (("frontend-web",), ("frontend/web/develop/TESTING.md", "frontend/web/design/ACCESSIBILITY.md")),
    "mobile-ui": (("frontend-app",), ("frontend/app/develop/TESTING.md", "frontend/app/design/LAYOUT.md")),
    "commit": ((), ("core/GIT_COMMIT_CONVENTION.md",)),
    "rule-maintenance": ((), ("core/RULER_MAINTENANCE.md", "core/DOC_GOVERNANCE.md")),
}


def task_budgets() -> dict:
    registry = json.loads((SKILL_ROOT / "templates/domain-registry.json").read_text())["domains"]
    domains = tuple(name for name in registry if name != "core")
    with runtime_fixture(domains=domains) as root:
        cli = SKILL_ROOT / "scripts/rulers_init.py"
        for name in domains:
            config = registry[name]
            if config["render_mode"] != "project-generated":
                continue
            candidate = root / "budget-candidates" / name
            for filename in config["templates"]:
                source = SKILL_ROOT / "templates/runtime" / config["template_root"] / filename
                text = source.read_text().replace("{{RULERS_DIR}}", "documents/rulers")
                text = re.split(r"(?m)^##\s+(?:\d+\.\s+)?AI_FILL", text)[0].rstrip() + "\n"
                target = candidate / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            plan = root / f"budget-{name}.json"
            for args in (
                ("rules-plan", "--domain", name, "--candidate-dir", str(candidate.relative_to(root)), "--reason",
                 "Synthetic template-content measurement", "--activate-on-apply", "--output", str(plan)),
                ("rules-apply", "--plan", str(plan), "--reviewed-by", "synthetic-budget",
                 "--evidence", "measurement-only-not-human-approval"),
            ):
                selectors = ("--project-root", str(root)) if args[0] == "rules-plan" else ()
                result = subprocess.run([sys.executable, str(cli), *args, *selectors],
                                        cwd=root, capture_output=True, text=True,
                                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                if result.returncode:
                    raise ValueError(result.stderr or result.stdout)
        inspection = inspect_project(project_root=root, rulers_dir="documents/rulers")
        if inspection.issues:
            raise ValueError([issue.to_dict() for issue in inspection.issues])
        entry_bytes = sum((root / name).stat().st_size for name in ("AGENTS.md", "documents/rulers/AGENTS.md"))
        rows = []
        for task, (selected_domains, rules) in TASKS.items():
            bundle = build_load_bundle(inspection, domains=selected_domains, rules=rules)
            context_bytes = len(runtime_context_json(build_runtime_context(inspection, requested_domains=selected_domains)))
            total = entry_bytes + bundle["bytes"] + context_bytes
            rows.append({"task": task, "files": bundle["files"], "bundle_bytes": bundle["bytes"],
                         "direct_load_bytes": entry_bytes + bundle["bytes"], "with_discovery_bytes": total,
                         "within_budget": total <= BUDGETS["fixed_chain_bytes"]})
        return {"source": "template-derived-isolated-runtime", "model_evaluation": False,
                "byte_accounting": "UTF-8 including markers and separators, excluding CLI trailing newline",
                "limit": BUDGETS["fixed_chain_bytes"], "tasks": rows,
                "all_pass": all(row["within_budget"] for row in rows)}


if __name__ == "__main__":
    report = task_budgets()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["all_pass"] else 1)
