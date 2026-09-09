"""Disposable synthetic target for development checks, never a real installation.

Review identities and domain contents are test data. Lifecycle transitions run
through the distributed CLI; no state from this development repository is used.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "ai-rulers-init"
REVIEW = (
    "--reviewed-by", "synthetic-fixture",
    "--evidence", "automated-test-only-not-human-approval",
    "--reviewed-at", "2026-09-08T00:00:00+00:00",
)


@contextmanager
def runtime_fixture(
    *, rulers_dir: str = "documents/rulers", domains: Sequence[str] = (),
) -> Iterator[Path]:
    """Yield a validated runtime project and remove it on exit."""
    registry = json.loads(
        (SKILL_ROOT / "templates/domain-registry.json").read_text(encoding="utf-8")
    )["domains"]
    ordered: list[str] = []

    def include(domain: str, visiting: frozenset[str] = frozenset()) -> None:
        if domain not in registry or domain == "core":
            raise ValueError(f"Unknown fixture domain: {domain}")
        if domain in visiting:
            raise ValueError(f"Cyclic fixture domain dependency: {domain}")
        if domain in ordered:
            return
        for dependency in registry[domain]["requires_active"]:
            if dependency != "core":
                include(dependency, visiting | {domain})
        ordered.append(domain)

    for domain in domains:
        include(domain)

    with tempfile.TemporaryDirectory(prefix="ai-rulers-runtime-") as temporary:
        project = Path(temporary).resolve()
        cli = SKILL_ROOT / "scripts/rulers_init.py"
        validator = SKILL_ROOT / "scripts/validate_rulers.py"

        def run(script: Path, *args: str) -> None:
            result = subprocess.run(
                [sys.executable, str(script), *args], cwd=project,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout)

        target = ("--project-root", str(project), "--rulers-dir", rulers_dir)
        plan = project / "fixture-plan.json"
        run(cli, "plan", *target, "--policy", "strict-cn", "--output", str(plan))
        run(cli, "apply", "--project-root", str(project), "--plan", str(plan))
        run(validator, "--mode", "candidate", *target)
        profile = project / rulers_dir / "PROJECT_PROFILE.md"
        profile.write_text(
            "# 项目画像\n\n## 项目身份\n\n"
            "- 项目名称：synthetic-runtime-fixture\n"
            "- 用途：自动化结构测试，非真实项目审阅\n\n"
            "## 命令\n\n- 验证：生成目录中的 scripts/validate_rulers.py\n\n"
            "## 当前有效事实与约束\n\n"
            "| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 临时测试项目 | observed | scripts/runtime_fixture.py | core | high |\n\n"
            "## 阻塞性未决问题\n\n| 问题 | 重要原因 | 作用域 | 必需审阅人 |\n| --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
        run(cli, "review-profile", *target, *REVIEW)
        for domain in ordered:
            config = registry[domain]
            if config["render_mode"] == "deterministic":
                command = "render-domain-candidate"
            else:
                command = "register-domain-candidate"
                for filename in config["templates"]:
                    path = project / rulers_dir / config["target_dir"] / filename
                    path.parent.mkdir(parents=True, exist_ok=True)
                    links = "\n".join(
                        f"- [{other}]({rulers_dir}/{config['target_dir']}/{other})"
                        for other in config["templates"] if other != filename
                    ) if filename == "INDEX.md" else ""
                    path.write_text(
                        f"# Synthetic {domain}: {filename}\n\n"
                        "```yaml\nmetadata:\n  applies_to:\n    - '**/*'\n"
                        f"  trigger_keywords:\n    - {domain}\n  must_load_with:\n"
                        f"    - {rulers_dir}/AGENTS.md\n```\n\n"
                        "Synthetic rule for lifecycle tests only.\n" + links + "\n",
                        encoding="utf-8",
                    )
            run(cli, command, *target, "--domain", domain)
            run(validator, "--mode", "candidate", *target)
            run(cli, "activate-domain", *target, "--domain", domain, *REVIEW)
        run(cli, "mark-runtime-ready", *target)
        run(project / rulers_dir / "scripts/validate_rulers.py", "--mode", "runtime", *target)
        yield project
