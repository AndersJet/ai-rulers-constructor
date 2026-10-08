#!/usr/bin/env python3
"""Prepare retained, synthetic interop targets using an explicit unpacked Skill.

This constructs inputs, not expected answers or human approval. Review metadata
is test-only. Grading lives outside the target; this script never runs a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REVIEW = ("--reviewed-by", "synthetic-interop-fixture",
          "--evidence", "automated-test-only-not-human-approval",
          "--reviewed-at", "2026-10-08T00:00:00+00:00")
SCENARIOS = ("chart", "continue", "rebuild", "interview")


def run(cwd: Path, *args: str) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode:
        raise RuntimeError(f"{args[0]} exited {result.returncode}: {result.stderr or result.stdout}")
    return result.stdout


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def snapshot(root: Path) -> dict:
    """Observable Git and file identity, excluding Git internals."""
    return {
        "head": run(root, "git", "rev-parse", "HEAD").strip(),
        "status": run(root, "git", "status", "--porcelain=v1"),
        "branches": run(root, "git", "for-each-ref", "--format=%(refname:short) %(upstream:short)", "refs/heads"),
        "worktrees": run(root, "git", "worktree", "list", "--porcelain"),
        "files": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.relative_to(root).parts},
    }


def prepare(skill: Path, root: Path, *, strategy: str, scenario: str, skills: Path,
            policy: str = "project-native") -> dict:
    if root.exists():
        raise ValueError(f"Refusing to overwrite existing target: {root}")
    root.mkdir(parents=True)
    run(root, "git", "init", "-b", "main")
    run(root, "git", "config", "user.name", "Synthetic Fixture")
    run(root, "git", "config", "user.email", "fixture@example.invalid")
    write(root, ".gitignore", "/.rulers-work/\n")
    write(root, "app.py", 'def session_usage():\n    return "unknown"\n')
    branch_policy = (
        "规划与研究复用 topic/decision-map；独立报告放 docs/research。隔离确有需要时允许 detached worktree。"
        if strategy == "detached" else
        "本项目规划使用 task/map；研究直接在该分支各写独立报告。隔离需求先确认，不默认创建 detached worktree。"
    )
    write(root, "docs/agents/workflow.md", "# 项目工作流\n\n" + branch_policy +
          "\n分支起点为本地 main；新任务分支无 upstream，未授权提交或推送。"
          "研究完成先回收报告并记录路径和身份，再讨论工作区归档；未知修改保留。\n")
    write(root, "docs/agents/tracker.md", """# Local Markdown tracker

Map: docs/map.md is the index; tickets live under docs/tickets. Each ticket has
Type, Status, Assignee, Parent and Blocked-by fields. Create children first,
then wire dependencies by relative links. Claim an open unblocked ticket by
setting Assignee; resolve by appending Resolution, setting closed, and linking
the report from the map. Maps use named links. Process only the selected ticket
on continuation. Retired maps remain linked from replacement maps.
Recovery: docs/assets.md records retained snapshots when a worktree is absent.
""")
    write(root, "docs/agents/domain.md", "# Domain docs\n\nCONTEXT.md 保存术语；accepted ADR 保存长期决定并引用 ticket；候选讨论留在 ticket。\n")
    write(root, "CONTEXT.md", "# 领域词汇\n\nSession usage: 最终 session 量；缺失保持 unknown。\n")
    write(root, "sources/alpha.md", "# Session source\n\nMember-window values discover session IDs only. Final usage is keyed by session ID. Missing usage is unknown.\n")
    write(root, "sources/beta.md", "# Attribution source\n\nProject path and Git remote identify repository attribution. A remote value does not establish permission or upstream policy.\n")
    skill_hashes = {}
    for name in ("wayfinder", "research", "grilling", "grill-with-docs", "domain-modeling"):
        source = skills / name
        destination = root / ".agents/skills" / name
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        skill_hashes[name] = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(source.rglob("*")) if p.is_file() and p.name != ".DS_Store"}
    profile = """# 项目画像

## 项目身份

- 项目名称：synthetic-interop
- 用途：隔离评测，非业务项目审阅

## 命令

- 验证：python3 documents/rulers/scripts/validate_rulers.py --mode runtime

## 当前有效事实与约束

| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |
| --- | --- | --- | --- | --- |
| Git 与工作区按 docs/agents/workflow.md | observed | docs/agents/workflow.md | core | high |
| 地图与恢复按 docs/agents/tracker.md | observed | docs/agents/tracker.md | core | high |
| 术语与决定按 docs/agents/domain.md | observed | docs/agents/domain.md | core | high |

## 阻塞性未决问题

| 问题 | 重要原因 | 作用域 | 必需审阅人 |
| --- | --- | --- | --- |
"""
    write(root, "fixture-profile.md", profile)
    cli = skill / "scripts/rulers_init.py"
    target = ("--project-root", str(root), "--rulers-dir", "documents/rulers")
    cli_log = []
    def call(*args: str) -> str:
        output = run(root, sys.executable, str(cli), *args)
        cli_log.append({"args": list(args), "stdout": output})
        return output
    call("plan", *target, "--policy", policy, "--candidate-profile", str(root / "fixture-profile.md"), "--output", str(root / "fixture-plan.json"))
    call("apply", "--project-root", str(root), "--plan", str(root / "fixture-plan.json"))
    call("review-profile", *target, *REVIEW)
    call("mark-runtime-ready", *target)
    validator = root / "documents/rulers/scripts/validate_rulers.py"
    checks = {}
    for mode in ("candidate", "runtime", "context", "load"):
        checks[mode] = run(root, sys.executable, str(validator), "--mode", mode, *target)
    checks["repeat_plan"] = call("plan", *target)
    for name in ("fixture-profile.md", "fixture-plan.json"):
        (root / name).unlink()
    if scenario != "chart":
        write(root, "docs/map.md", """# Session usage decision map

## Destination
确定 Session ID 最终用量与项目归属的规格；本轮只作决定。
## Notes
Use wayfinder and project tracker/workflow. Source: synthetic-current-map.
## Decisions so far
- [固定人类回答](tickets/answered.md): 规划分支复用与研究报告回收。
## Not yet specified
## Out of scope
业务实现、提交与推送。
""")
        write(root, "docs/tickets/answered.md", "# 固定人类回答\nType: grilling\nStatus: closed\nAssignee: human\nParent: ../map.md\nBlocked-by: none\n\n## Resolution\n历史人类回答：一个需求复用一个规划分支，研究者分别保存独立报告；确需隔离时采用 detached worktree，结果回收到规划目录后再回收工作区。来源为 handoff 引用的 implementation-decisions.md 第一轮 Q1；这是固定回答回放，不是实时 HITL。本夹具的规格 Destination 为合成任务输入，不是该历史用户的业务需求。\n")
        write(root, "docs/tickets/research.md", "# Final usage facts\nType: research\nStatus: open\nAssignee: none\nParent: ../map.md\nBlocked-by: none\n\n## Question\nInvestigate sources/alpha.md and record the final usage boundary in docs/research/final-usage.md.\n")
    if scenario == "continue":
        write(root, "docs/imported-map.md", "# Imported fork map\nSource: synthetic-other-effort\nDestination: Implement production collection now.\n")
    if scenario == "rebuild":
        write(root, "docs/research/old-study.md", "# 旧研究\nSession ID discovery is separate from final usage.\n")
        write(root, "docs/assets.md", "# 资产目录\n旧工作区 /missing/old-research 当前不可见；保留快照 docs/research/old-study.md。\n")
    if scenario == "interview":
        write(root, "docs/tickets/interview.md", "# Unknown usage semantics\nType: grilling\nStatus: open\nAssignee: none\nParent: ../map.md\nBlocked-by: none\n\n## Question\n本轮讨论规划和研究成果的保存方式。工作区回收方式已有历史回答；旧分支何时允许删除尚未回答。\n")
    run(root, "git", "add", ".")
    run(root, "git", "commit", "-m", "fixture: synthetic baseline")
    run(root, "git", "switch", "--no-track", "-c", "topic/decision-map" if strategy == "detached" else "task/map", "main")
    if scenario == "rebuild":
        write(root, "personal-draft.txt", "Unknown owner draft. Retain this exact content.\n")
    return {"strategy": strategy, "scenario": scenario, "policy": policy, "skill_root": str(skill),
            "skills_original_root": str(skills), "global_skill_hashes": skill_hashes,
            "cli": cli_log, "checks": checks, "before": snapshot(root)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--skills-root", type=Path, required=True)
    parser.add_argument("--strategy", choices=("detached", "named"), required=True)
    parser.add_argument("--policy", choices=("project-native", "strict-cn"), default="project-native")
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    args = parser.parse_args()
    evidence = prepare(args.skill_root.resolve(), args.target.resolve(), strategy=args.strategy,
                       scenario=args.scenario, skills=args.skills_root.resolve(), policy=args.policy)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.target.resolve())


if __name__ == "__main__":
    main()
