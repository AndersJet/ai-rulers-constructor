from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class UnknownPolicyError(ValueError):
    pass


def load_policy(skill_root: Path, policy_id: str) -> dict[str, Any]:
    path = skill_root / "templates" / "policies" / f"{policy_id}.json"
    if not path.is_file():
        raise UnknownPolicyError(f"Unknown rulers policy: {policy_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def policy_blocks(policy: dict[str, Any], rulers_dir: str) -> tuple[str, str]:
    if policy.get("id") != "strict-cn":
        return "", ""
    inline = f"""## 提交策略

- commit type 使用英文，subject/body 使用中文。
- feat/fix 提交前必须更新 CHANGELOG.md。
- 进入提交流程前加载 `{rulers_dir}/core/GIT_COMMIT_CONVENTION.md` 和
  `{rulers_dir}/core/CHANGELOG_MAINTENANCE.md`。
"""
    route = f"""| git 提交、暂存、CHANGELOG、发布说明 | `{rulers_dir}/core/GIT_COMMIT_CONVENTION.md`、`{rulers_dir}/core/CHANGELOG_MAINTENANCE.md` |
"""
    return inline, route
