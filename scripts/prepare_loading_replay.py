"""Create a retained natural-task target for loading/continuation replay.

All approvals are synthetic fixture data. Scoring and hidden checks belong outside
the target. Does not run models, install global skills or modify existing targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts.prepare_interop_eval import run, write, snapshot


PROMPTS = {
    "fix": "修复 cart.py 的 subtotal：每项单价需要乘以 quantity，空购物车返回零。完成必要验证并报告结果。不要提交。",
    "blocked-choice": "手续费有 fixed 和 percentage 两种候选，费率尚未决定，需要我选择。先处理可以独立完成的工作：修复 subtotal 没有乘 quantity 的问题并验证；不要替我决定手续费，也不要提交。",
    "research": "本轮只评估 docs/fee-options.md 中的两个手续费方案，将比较和需要我决定的问题写入 docs/fee-review.md。本轮不改实现、不提交。",
}


def prepare(skill: Path, target: Path, scenario: str) -> dict:
    skill, target = skill.resolve(), target.resolve()
    if target.exists():
        raise ValueError(f"Refusing to overwrite target: {target}")
    if scenario not in PROMPTS or not (skill / "scripts/rulers_init.py").is_file():
        raise ValueError("Unknown scenario or missing Skill")
    target.mkdir(parents=True)
    run(target, "git", "init", "-b", "main")
    run(target, "git", "config", "user.name", "Synthetic Replay")
    run(target, "git", "config", "user.email", "fixture@example.invalid")
    write(target, "cart.py", 'def subtotal(rows):\n    return sum(row["unit_price"] for row in rows)\n\ndef fee(amount):\n    return None\n')
    write(target, "test_cart.py", '''import unittest
from cart import subtotal

class CartTest(unittest.TestCase):
    def test_one_item(self):
        self.assertEqual(subtotal([{"unit_price": 120, "quantity": 1}]), 120)

if __name__ == "__main__":
    unittest.main()
''')
    write(target, "docs/fee-options.md", "# Fee options\n\nfixed: 20 cents per order. percentage: 2 percent rounded down. Owner has not selected either option.\n")
    write(target, "README.md", "# Cart fixture\n\nAmounts are integer cents. Run `python3 -m unittest` from the project root. No network or production access.\n")
    write(target, "notes.txt", "Unrelated human note: preserve this byte for byte.\n")
    metadata = "```yaml\nmetadata:\n  applies_to:\n    - '*.py'\n  trigger_keywords:\n    - cart\n  must_load_with: []\n```\n"
    write(target, ".rulers-work/candidate/backend/INDEX.md", "# Cart backend\n\n" + metadata + "\nBehavior changes: [TESTING.md](TESTING.md)\n")
    testing = (skill / "templates/runtime/domains/backend/TESTING.md").read_text().replace("{{RULERS_DIR}}", "documents/rulers")
    testing = re.split(r"(?m)^##\s+AI_FILL", testing)[0]
    write(target, ".rulers-work/candidate/backend/TESTING.md", testing + "\nProject test command: `python3 -m unittest` at project root.\n")
    write(target, ".rulers-work/candidate/profile.md", """# 项目画像

## 项目身份

- 名称：合成购物车回放，不是业务项目

## 命令

- 测试：项目根运行 `python3 -m unittest`；使用可丢弃本地数据，无生产访问

## 当前有效事实与约束

| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |
| --- | --- | --- | --- | --- |
| 金额为整数分，使用标准库 unittest | observed | README.md | backend | high |

## 阻塞性未决问题

| 问题 | 重要原因 | 作用域 | 必需审阅人 |
| --- | --- | --- | --- |
| 手续费方案尚未选择，仅阻塞手续费实现 | docs/fee-options.md 中两个候选需选择 | backend | fixture owner |
""")
    spec = {"projects": {"workspace": {"profile": ".rulers-work/candidate/profile.md",
              "domains": {"backend": ".rulers-work/candidate/backend"}}}}
    write(target, ".rulers-work/candidates.json", json.dumps(spec))
    import sys
    cli = str(skill / "scripts/rulers_init.py")
    planned = json.loads(run(target, sys.executable, cli, "init-plan", "--project-root", str(target),
                             "--candidates", ".rulers-work/candidates.json"))
    if planned["status"] != "review":
        raise ValueError(planned)
    run(target, sys.executable, cli, "init-apply", "--plan", str(target / planned["plan_path"]),
        "--reviewed-by", "synthetic-loading-eval", "--evidence", "fixture-only-not-human-approval")
    run(target, "git", "add", "AGENTS.md", ".gitignore", "cart.py", "test_cart.py", "README.md", "notes.txt", "docs", "documents")
    run(target, "git", "commit", "-m", "test: 初始化隔离回放夹具")
    return {"scenario": scenario, "target": str(target), "prompt": PROMPTS[scenario],
            "skill_files": {str(p.relative_to(skill)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(skill.rglob("*")) if p.is_file() and "__pycache__" not in p.parts},
            "before": snapshot(target), "synthetic": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--scenario", choices=tuple(PROMPTS), required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    if args.evidence.exists() or args.evidence.resolve().is_relative_to(args.target.resolve()):
        raise ValueError("Evidence must be a new path outside the target")
    record = prepare(args.skill, args.target, args.scenario)
    args.evidence.mkdir(parents=True)
    write(args.evidence, "fixture.json", json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    write(args.evidence, "prompt.txt", record["prompt"])
    print(json.dumps({"target": str(args.target), "evidence": str(args.evidence)}))
