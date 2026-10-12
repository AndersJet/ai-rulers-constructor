from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills/ai-rulers-init"
CLI = SKILL_ROOT / "scripts/rulers_init.py"
VALIDATOR = SKILL_ROOT / "scripts/validate_rulers.py"

sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from rulers_lib.state import file_sha256, state_json


_FIXTURE_ROOT = ROOT / "tests/fixtures/ai-rulers-v2"
_REVIEWED_AT = "2026-07-20T10:00:00+08:00"
_PROFILE_TEXT = """# 项目画像

## 项目身份

- 项目名称：fixture-project
- 仓库形态：application

## 命令

| 用途 | 命令 | 工作目录 | 证据 |
| --- | --- | --- | --- |
| 测试 | `python3 -m unittest` | 项目根目录 | fixture |

## 当前有效事实与约束

| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |
| --- | --- | --- | --- | --- |
| Python runtime | observed | pyproject.toml | core | high |

## 阻塞性未决问题

| 问题 | 重要原因 | 作用域 | 必需审阅人 |
| --- | --- | --- | --- |
| 无 | fixture baseline | core | fixture-owner |
"""
_CORE_TEXT = """# Fixture Hard Constraints

```yaml
metadata:
  applies_to:
    - "**/*"
  trigger_keywords:
    - fixture-core
  must_load_with:
    - documents/custom-rulers/AGENTS.md
```

Fixture core rule content.
"""
_BACKEND_TEXT = """# Fixture Backend Index

```yaml
metadata:
  applies_to:
    - "server/**"
  trigger_keywords:
    - backend
  must_load_with:
    - documents/custom-rulers/AGENTS.md
```

Project-generated backend rule content.
"""


def run_cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )


def run_validator(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )


def read_state(project: Path, rulers_dir: str = "documents/rulers") -> dict[str, Any]:
    state_path = project / rulers_dir / "RULERS_STATE.json"
    return json.loads(state_path.read_text(encoding="utf-8"))


def write_profile(
    project: Path,
    rows: Sequence[tuple[str, str, str, str, str]],
    *,
    unresolved: Sequence[tuple[str, str, str, str]] = (),
    rulers_dir: str = "documents/rulers",
) -> Path:
    confirmed_rows = "\n".join(
        f"| {content} | {basis} | {evidence} | {scope} | {confidence} |"
        for content, basis, evidence, scope, confidence in rows
    )
    unresolved_rows = "\n".join(
        f"| {question} | {reason} | {scope} | {reviewer} |"
        for question, reason, scope, reviewer in unresolved
    )
    if not unresolved_rows:
        unresolved_rows = "|  |  |  |  |"
    profile_text = f"""# 项目画像

## 项目身份

- 项目名称：test-project
- 仓库形态：application

## 命令

| 用途 | 命令 | 工作目录 | 证据 |
| --- | --- | --- | --- |
| 测试 | `python3 -m unittest` | 项目根目录 | test-support |

## 当前有效事实与约束

| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |
| --- | --- | --- | --- | --- |
{confirmed_rows}

## 阻塞性未决问题

| 问题 | 重要原因 | 作用域 | 必需审阅人 |
| --- | --- | --- | --- |
{unresolved_rows}
"""
    profile_path = project / rulers_dir / "PROJECT_PROFILE.md"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile_text, encoding="utf-8")
    return profile_path


def snapshot_project(
    project: Path,
    *,
    exclude_cold: bool = True,
) -> dict[str, tuple[bytes, int]]:
    snapshot: dict[str, tuple[bytes, int]] = {}
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if exclude_cold and relative.parts[0] in {".plans", ".transactions"}:
            continue
        if path.is_file():
            snapshot[relative.as_posix()] = (path.read_bytes(), path.stat().st_mtime_ns)
    return snapshot


def materialize_v2_fixture(
    project: Path,
    fixture_name: str,
) -> tuple[Path, dict[str, Any]]:
    if Path(fixture_name).name != fixture_name:
        raise ValueError(f"fixture_name must be a filename: {fixture_name}")
    fixture_path = _FIXTURE_ROOT / fixture_name
    state = json.loads(fixture_path.read_text(encoding="utf-8"))
    rulers_root = project / state["rulers_dir"]
    content_by_relative = {
        "PROJECT_PROFILE.md": _PROFILE_TEXT.encode("utf-8"),
        "core/HARD_CONSTRAINTS.md": _CORE_TEXT.encode("utf-8"),
        "backend/INDEX.md": _BACKEND_TEXT.encode("utf-8"),
    }
    for relative, content in content_by_relative.items():
        path = rulers_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    profile_hash = file_sha256(rulers_root / "PROJECT_PROFILE.md")
    state["profile"]["content_sha256"] = profile_hash
    for relative in content_by_relative:
        project_relative = (Path(state["rulers_dir"]) / relative).as_posix()
        metadata = state["managed_files"][project_relative]
        current_hash = file_sha256(project / project_relative)
        metadata["rendered_sha256"] = current_hash
        if "source_sha256" in metadata:
            metadata["source_sha256"] = current_hash

    state_path = rulers_root / "RULERS_STATE.json"
    state_path.write_text(state_json(state), encoding="utf-8")
    return state_path, state


def apply_reviewed_plan(project: Path, plan_path: Path) -> dict[str, Any]:
    result = run_cli(
        "apply",
        "--project-root",
        str(project),
        "--plan",
        str(plan_path),
        "--reviewed-by",
        "test-owner",
        "--evidence",
        "test-review",
        "--reviewed-at",
        _REVIEWED_AT,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout)
