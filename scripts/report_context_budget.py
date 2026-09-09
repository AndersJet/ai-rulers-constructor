#!/usr/bin/env python3
"""Context budget measurement and load-graph report for ai-rulers-init.

Hard gate: only imports validation.BUDGETS and uses lines/UTF-8 bytes/
compact JSON/path set.  Optionally imports tiktoken for o200k_base token
trend; when unavailable, token fields are null and the gate still passes.
"""
from __future__ import annotations

import argparse
import json
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-rulers-init"

sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from rulers_lib.validation import (  # noqa: E402
    BUDGETS,
    build_runtime_context,
    inspect_project,
    runtime_context_json,
)


def _skill_lines() -> int:
    skill_md = SKILL_ROOT / "SKILL.md"
    if not skill_md.is_file():
        return 0
    return len(skill_md.read_text(encoding="utf-8").splitlines())


def _context_bytes_for_project(
    project_root: Path,
    rulers_dir: str,
    domains: Sequence[str] = (),
) -> int:
    inspection = inspect_project(project_root=project_root, rulers_dir=rulers_dir)
    context = build_runtime_context(inspection, requested_domains=domains)
    return len(runtime_context_json(context))


def build_load_graph(
    context: Mapping[str, Any], *, selected_domains: Sequence[str]
) -> dict[str, Any]:
    """Build the load graph from a runtime context dict.

    The load graph lists exactly which files an agent would load for the
    given domain selection.  It excludes RULERS_STATE.json, runtime INDEX.md
    references, sibling domain files, and anything not in the context load
    set.
    """
    load = context.get("load") or {}
    core_files = list(load.get("core") or [])
    index_files = list(load.get("indexes") or [])
    routes = context.get("routes") or {}

    profile = context.get("profile") or {}
    profile_path = profile.get("path", "")

    graph: dict[str, Any] = {
        "core": core_files,
        "profile": profile_path,
        "domain_indexes": index_files,
        "selected_domains": sorted(selected_domains),
        "routes": {d: routes.get(d, {}) for d in sorted(selected_domains)},
        "total_files": len(core_files) + len(index_files) + (1 if profile_path else 0),
    }
    return graph


def _measure_growth_managed(project_root: Path, rulers_dir: str, domains: Sequence[str]) -> dict[str, Any]:
    from rulers_lib.state import state_json, file_sha256
    with tempfile.TemporaryDirectory(prefix="rulers-growth-") as td:
        project = Path(td) / "target"
        shutil.copytree(project_root, project)
        state_path = project / rulers_dir / "RULERS_STATE.json"
        if not state_path.is_file():
            return {"delta_bytes": 0, "pass": False, "reason": "No installed State"}
        state = json.loads(state_path.read_text(encoding="utf-8"))
        base_count = len(state["managed_files"])
        sizes = []
        for i in range(100):
            relative = f"{rulers_dir}/budget-rules/rule-{i}.md"
            path = project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Synthetic growth rule\n", encoding="utf-8")
            state["managed_files"][relative] = {"ownership": "managed", "rendered_sha256": file_sha256(path)}
            if i in (0, 99):
                state_path.write_text(state_json(state), encoding="utf-8")
                sizes.append(_context_bytes_for_project(project, rulers_dir, domains))
        return {"baseline_managed_files": base_count, "added_files": [1, 100],
                "managed_1_bytes": sizes[0], "managed_100_bytes": sizes[1],
                "delta_bytes": sizes[1] - sizes[0], "pass": sizes[0] == sizes[1]}


def _measure_growth_reconcile(project_root: Path, rulers_dir: str, domains: Sequence[str]) -> dict[str, Any]:
    from rulers_lib.plans import create_plan
    from rulers_lib.apply import apply_plan_unified
    with tempfile.TemporaryDirectory(prefix="rulers-reconcile-") as td:
        project = (Path(td) / "target").resolve()
        shutil.copytree(project_root, project)
        state_path = project / rulers_dir / "RULERS_STATE.json"
        if not state_path.is_file():
            return {"delta_bytes": 0, "pass": False, "reason": "No installed State"}
        original = state_path.read_bytes()
        candidate = project / "budget-profile.md"
        candidate.write_bytes((project / rulers_dir / "PROJECT_PROFILE.md").read_bytes())
        first = _context_bytes_for_project(project, rulers_dir, domains)
        for _ in range(20):
            plan = create_plan(skill_root=SKILL_ROOT, project_root=project, rulers_dir=rulers_dir,
                               operation="reconcile", candidate_profile=candidate)
            path = project / rulers_dir / ".plans" / plan["plan_id"] / "plan.json"
            result = apply_plan_unified(path, skill_root=SKILL_ROOT, project_root=project,
                                       reviewed_by="synthetic-budget", evidence="test-only-zero-diff")
            if result["changed_files"]:
                raise ValueError("Zero-diff reconcile unexpectedly changed files")
        last = _context_bytes_for_project(project, rulers_dir, domains)
        return {"reconcile_0_bytes": first, "reconcile_20_bytes": last, "executed_reconciles": 20,
                "delta_bytes": last - first, "pass": last == first and state_path.read_bytes() == original}


def _token_count(text: str) -> int | None:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text))
    except (ImportError, Exception):
        return None


def measure_context_budget(
    *,
    project_root: Path | None = None,
    rulers_dir: str = "documents/rulers",
    domains: Sequence[str] = (),
    include_token_trend: bool = True,
) -> dict[str, Any]:
    """Produce the full budget measurement report as a dict."""
    if project_root is None:
        from scripts.runtime_fixture import runtime_fixture

        with runtime_fixture(rulers_dir=rulers_dir, domains=domains) as project:
            report = measure_context_budget(
                project_root=project, rulers_dir=rulers_dir, domains=domains,
                include_token_trend=include_token_trend,
            )
            report["measurement_source"] = "isolated-synthetic-runtime"
            return report

    skill_lines = _skill_lines()
    context_bytes = _context_bytes_for_project(project_root, rulers_dir, domains)

    inspection = inspect_project(project_root=project_root, rulers_dir=rulers_dir)
    context = build_runtime_context(inspection, requested_domains=domains)
    context_json = runtime_context_json(context)
    load_graph = build_load_graph(context, selected_domains=list(domains))

    healthy = context["phase"] == "runtime_ready" and not inspection.issues
    growth_managed = _measure_growth_managed(project_root, rulers_dir, domains) if healthy else {"pass": False, "delta_bytes": 0}
    growth_reconcile = _measure_growth_reconcile(project_root, rulers_dir, domains) if healthy else {"pass": False, "delta_bytes": 0}
    from rulers_lib.rule_loading import build_load_bundle
    bundle = build_load_bundle(inspection, domains=domains) if healthy else {"bytes": 0, "within_budget": False}
    entry_bytes = sum((project_root / path).stat().st_size for path in ("AGENTS.md", f"{rulers_dir}/AGENTS.md") if (project_root / path).is_file())


    tokenizer_result: dict[str, Any] = {"available": False, "encoding": None, "context_tokens": None}
    if include_token_trend:
        tokens = _token_count(context_json.decode("utf-8"))
        if tokens is not None:
            tokenizer_result = {
                "available": True,
                "encoding": "o200k_base",
                "context_tokens": tokens,
            }

    limits = dict(BUDGETS)
    measurements = {
        "skill_lines": skill_lines,
        "context_bytes": context_bytes,
        "loaded_content_bytes": bundle["bytes"],
        "fixed_chain_bytes": entry_bytes + bundle["bytes"] + context_bytes,
    }

    checks: list[dict[str, Any]] = []
    checks.append({
        "name": "healthy_runtime",
        "pass": context["phase"] == "runtime_ready" and not inspection.issues,
    })
    checks.append({
        "name": "skill_lines",
        "limit": limits["skill_lines"],
        "actual": skill_lines,
        "pass": skill_lines <= limits["skill_lines"],
    })
    checks.append({
        "name": "context_bytes",
        "limit": limits["context_bytes"],
        "actual": context_bytes,
        "pass": context_bytes <= limits["context_bytes"],
    })
    checks.append({"name": "fixed_chain_bytes", "actual": measurements["fixed_chain_bytes"], "limit": limits["fixed_chain_bytes"], "pass": measurements["fixed_chain_bytes"] <= limits["fixed_chain_bytes"]})
    checks.append({
        "name": "managed_growth",
        "limit": 0,
        "actual": growth_managed["delta_bytes"],
        "pass": growth_managed["pass"],
    })
    checks.append({
        "name": "reconcile_growth",
        "limit": 0,
        "actual": growth_reconcile["delta_bytes"],
        "pass": growth_reconcile["pass"],
    })

    return {
        "measurement_source": "explicit-project",
        "limits": limits,
        "measurements": measurements,
        "load_graph": load_graph,
        "growth": {
            "managed_1_to_100": growth_managed,
            "reconcile_0_to_20": growth_reconcile,
        },
        "tokenizer": tokenizer_result,
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks),
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"Measurement source: {report['measurement_source']}")
    lines.append("")
    lines.append("# Context \u9884\u7b97\u62a5\u544a")
    lines.append("")
    lines.append("> \u7531 scripts/report_context_budget.py \u81ea\u52a8\u751f\u6210")
    lines.append("")
    lines.append("## \u9884\u7b97\u5e38\u91cf\u8868")
    lines.append("")
    lines.append("| \u6307\u6807 | \u9884\u7b97 | \u5f53\u524d\u5b9e\u9645 | \u72b6\u6001 |")
    lines.append("|------|------|----------|------|")
    limits = report["limits"]
    meas = report["measurements"]
    sl_ok = "\u2705" if meas["skill_lines"] <= limits["skill_lines"] else "\u274c"
    cb_ok = "\u2705" if meas["context_bytes"] <= limits["context_bytes"] else "\u274c"
    lines.append(f"| SKILL.md \u884c\u6570 | \u2264{limits['skill_lines']} | {meas['skill_lines']} | {sl_ok} |")
    lines.append(f"| Context JSON \u5b57\u8282 | \u2264{limits['context_bytes']} | {meas['context_bytes']} | {cb_ok} |")
    lines.append("")
    lines.append("## \u589e\u957f\u95e8\u7981")
    lines.append("")
    gm = report["growth"]["managed_1_to_100"]
    gr = report["growth"]["reconcile_0_to_20"]
    gm_ok = "\u2705" if gm["pass"] else "\u274c"
    gr_ok = "\u2705" if gr["pass"] else "\u274c"
    lines.append(f"- Managed 1\u2192100 \u6587\u4ef6\uff1adelta = {gm['delta_bytes']} bytes {gm_ok}")
    lines.append(f"- Reconcile 0\u219220 \u6b21\uff1adelta = {gr['delta_bytes']} bytes {gr_ok}")
    lines.append("")
    lines.append("## \u52a0\u8f7d\u56fe")
    lines.append("")
    lg = report["load_graph"]
    lines.append(f"- Core \u6587\u4ef6\uff1a{', '.join(lg['core'])}")
    lines.append(f"- Profile\uff1a{lg['profile']}")
    idx_str = ', '.join(lg['domain_indexes']) if lg['domain_indexes'] else '\uff08\u65e0\uff09'
    lines.append(f"- \u9886\u57df INDEX\uff1a{idx_str}")
    lines.append(f"- \u603b\u52a0\u8f7d\u6587\u4ef6\u6570\uff1a{lg['total_files']}")
    lines.append("")
    lines.append("## Tokenizer")
    lines.append("")
    tok = report["tokenizer"]
    if tok["available"]:
        lines.append(f"- \u7f16\u7801\uff1a{tok['encoding']}")
        lines.append(f"- Context tokens\uff1a{tok['context_tokens']}")
    else:
        lines.append("- token \u8d8b\u52bf\u672a\u8fd0\u884c\uff08tiktoken \u4e0d\u53ef\u7528\uff09")
    lines.append("")
    overall = "\u2705 \u5168\u90e8\u901a\u8fc7" if report["all_pass"] else "\u274c \u5b58\u5728\u672a\u901a\u8fc7\u9879"
    lines.append(f"**\u603b\u4f53\u7ed3\u679c\uff1a{overall}**")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure and report ai-rulers context budget."
    )
    parser.add_argument(
        "--project-root",
        help="Measure an installed target; default creates a disposable synthetic runtime.",
    )
    parser.add_argument("--rulers-dir", default="documents/rulers")
    parser.add_argument("--domain", action="append", default=[], dest="domains")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--check", action="store_true", help="Exit 1 if any check fails.")
    parser.add_argument("--markdown-output", metavar="PATH", help="Write Markdown report to PATH.")
    parser.add_argument("--no-tokenizer", action="store_true", help="Skip tiktoken token counting.")
    args = parser.parse_args(argv)

    report = measure_context_budget(
        project_root=Path(args.project_root) if args.project_root else None,
        rulers_dir=args.rulers_dir,
        domains=args.domains,
        include_token_trend=not args.no_tokenizer,
    )

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_render_markdown(report))

    if args.markdown_output:
        md_path = Path(args.markdown_output)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_render_markdown(report), encoding="utf-8")

    if args.check and not report["all_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
