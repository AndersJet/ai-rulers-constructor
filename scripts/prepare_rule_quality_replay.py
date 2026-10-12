"""Prepare raw project evidence or an installed maintenance fixture for model replay.

Discovery targets contain no generated Profile or expected rule answers. Synthetic
approval is used only to establish maintenance pre-state, never as a model result.
The caller keeps prompts, scoring and execution evidence outside the target.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts.prepare_interop_eval import run, snapshot, write


SCENARIOS = ("minimal", "boundary", "conflict", "greenfield", "maintenance")
METADATA = "```yaml\nmetadata:\n  applies_to:\n    - 'services/**'\n  trigger_keywords:\n    - refund\n  must_load_with: []\n```\n"
REVIEW = ("--reviewed-by", "synthetic-quality-fixture",
          "--evidence", "automated-prestate-only-not-human-approval")


def install_maintenance(skill: Path, target: Path) -> dict:
    """Install intentionally redundant legacy rules through the public CLI."""
    write(target, ".rulers-work/seed/backend/INDEX.md", "# Backend\n" + METADATA +
          "\nRefund changes: [REFUNDS.md](REFUNDS.md), [RETRIES.md](RETRIES.md).\n"
          "Receipt changes: [RECEIPTS.md](RECEIPTS.md).\nLogging: [LOGGING.md](LOGGING.md).\n")
    for name, body in {
        "REFUNDS": "退款金额使用整数分，累计退款不得超过实付；同一支付通知重复到达不得重复退款。依据 docs/refunds.md。",
        "RETRIES": "重复支付回调不得再次发放退款，保持退款幂等。依据 docs/refunds.md。",
        "RECEIPTS": "同一邮件回执重复到达不重复发信；回执去重由邮件系统维护。依据 docs/receipts.md。",
        "LOGGING": "旧约定：所有退款日志保存 90 天。",
    }.items():
        write(target, f".rulers-work/seed/backend/{name}.md", f"# {name}\n" + METADATA + "\n" + body + "\n")
    write(target, ".rulers-work/seed/profile.md", """# 项目画像

## 项目身份

- 项目名称：refund-quality-fixture，合成维护前态

## 命令

- 项目根运行 `python3 -m unittest discover -s tests`

## 当前有效事实与约束

| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |
| --- | --- | --- | --- | --- |
| 退款与邮件回执分别负责幂等 | observed | docs/refunds.md、docs/receipts.md | backend | high |

## 阻塞性未决问题

| 问题 | 重要原因 | 作用域 | 必需审阅人 |
| --- | --- | --- | --- |
""")
    write(target, ".rulers-work/seed.json", json.dumps({"projects": {"workspace": {
        "profile": ".rulers-work/seed/profile.md", "domains": {"backend": ".rulers-work/seed/backend"}}}}))
    cli = str(skill / "scripts/rulers_init.py")
    result = json.loads(run(target, sys.executable, cli, "init-plan", "--project-root", str(target),
                            "--candidates", ".rulers-work/seed.json"))
    run(target, sys.executable, cli, "init-apply", "--plan", str(target / result["plan_path"]), *REVIEW)
    return result


def prepare(skill: Path, target: Path, scenario: str) -> dict:
    skill, target = skill.resolve(), target.resolve()
    if scenario not in SCENARIOS or not (skill / "scripts/rulers_init.py").is_file():
        raise ValueError("Unknown scenario or missing Skill")
    if target.exists():
        raise ValueError(f"Refusing to overwrite target: {target}")
    target.mkdir(parents=True)
    run(target, "git", "init", "-b", "main")
    run(target, "git", "config", "user.name", "Synthetic Quality Fixture")
    run(target, "git", "config", "user.email", "fixture@example.invalid")
    write(target, "notes.txt", "Unrelated human note; preserve byte for byte.\n")
    write(target, "README.md", "# Refund example\n\nSynthetic local project. No deployment or remote access.\n"
          "Run `python3 -m unittest discover -s tests` from the root. Business evidence is in docs/.\n")
    write(target, "docs/refunds.md", "# Refund contract\n\n退款用整数分，累计退款不超过实付。"
          "支付回调可重复到达，同一通知只允许一次退款。浏览器只提交请求，不计算最终退款额度。\n")
    write(target, "services/refunds.py", """def refund(paid, refunded, amount, notice_id, seen):
    if notice_id in seen:
        return refunded
    if amount < 0 or refunded + amount > paid:
        raise ValueError('refund limit')
    seen.add(notice_id)
    return refunded + amount
""")
    write(target, "tests/test_refunds.py", """import unittest
from services.refunds import refund

class RefundTest(unittest.TestCase):
    def test_duplicate(self):
        seen = set()
        total = refund(100, 0, 20, 'n1', seen)
        self.assertEqual(refund(100, total, 20, 'n1', seen), 20)
    def test_limit(self):
        with self.assertRaises(ValueError):
            refund(100, 90, 20, 'n2', set())
""")
    if scenario in {"boundary", "conflict"}:
        write(target, "web/refunds.js", "export const requestRefund = (api, cents) => api.refund({cents});\n")
        write(target, "contracts/refund-event.json", json.dumps({"event": "refund.recorded", "fields": {
            "refunded_cents": "cumulative total, not this notification's increment", "notice_id": "payment notification id"}}, indent=2))
        write(target, "workers/receipts.py", "def receipt_total(event):\n    return event['refunded_cents']\n")
        write(target, "docs/ownership.md", "# Boundaries\n\nweb、services/refunds 和 workers/receipts 共同参与退款业务。"
              "支付服务拥有退款写入权，回执工作器只读取 refund.recorded。它们共用一个数据库。"
              "CODEOWNERS 仅指定代码维护者，不指定业务或生产批准人。\n")
        write(target, "CODEOWNERS", "/services/ @example-maintainer\n")
    if scenario == "conflict":
        write(target, "docs/decision.md", "# Approved design in this synthetic project\n\n"
              "已批准：退款写入只能经过支付服务，回执工作器只能消费事件。实现若不符合，应单列偏离。"
              "手续费算法仍待业务方决定，不得自行选择。\n")
        write(target, "workers/legacy_refund.py", "def legacy_refund(db, amount):\n    db.execute('UPDATE refunds SET cents = ?', (amount,))\n")
    if scenario == "greenfield":
        # Only files created above are removed; this target is exclusively new.
        for folder in ("services", "tests"):
            for path in (target / folder).iterdir():
                path.unlink()
            (target / folder).rmdir()
        write(target, "README.md", "# Planned refund product\n\n尚无代码、测试框架或部署设施。\n")
        write(target, "docs/decision.md", "# Approved design in this synthetic project\n\n"
              "退款契约已批准用于未来实现。实现语言、持久化和测试命令尚未决定。\n")
    if scenario == "maintenance":
        write(target, "docs/receipts.md", "# Receipt contract\n\n回执去重由独立邮件系统维护，重复回执不得重复发信。\n")
        write(target, "docs/logging.md", "# Logging decision\n\n旧退款日志 90 天约定已撤销。"
              "保留期交给部署环境的已批准保留政策，本项目不再规定固定天数；日志仍不得泄露凭据或客户数据。\n")
        install_maintenance(skill, target)
        task = ("维护当前 rulers：退款重复回调的要求似乎重复了，请合理合并；邮件回执的独立约束保留。"
                "按 docs/logging.md 删除旧日志天数约定，保留需要的保障。准备最小完整候选和可审阅计划，"
                "不要应用或编造批准。本轮不改业务代码，不提交。")
    else:
        task = ("使用指定 Skill 为当前项目准备初始化候选与集中审阅计划，依据现有材料决定必要范围。"
                "需要人类决定的内容请指出；本轮只准备，不应用、不修改业务实现、不提交。")
    run(target, "git", "add", ".")
    run(target, "git", "commit", "-m", "test: synthetic input baseline")
    prompt = f"本次使用的 Skill 位于 {skill}/SKILL.md。\n" + task
    return {"scenario": scenario, "target": str(target), "prompt": prompt, "synthetic": True,
            "synthetic_prestate_approval": scenario == "maintenance", "before": snapshot(target),
            "skill_files": {str(p.relative_to(skill)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(skill.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    evidence, target = args.evidence.resolve(), args.target.resolve()
    if evidence.exists() or evidence.is_relative_to(target) or target.is_relative_to(evidence):
        raise ValueError("Evidence and target must be new, separate paths")
    record = prepare(args.skill, target, args.scenario)
    evidence.mkdir(parents=True)
    write(evidence, "fixture.json", json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    write(evidence, "prompt.txt", record["prompt"])
    print(json.dumps({"target": str(target), "evidence": str(evidence)}))


if __name__ == "__main__":
    main()
