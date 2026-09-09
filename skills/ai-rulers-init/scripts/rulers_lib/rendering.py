"""Render framework templates; all lifecycle writes live in the unified apply path."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .policies import policy_blocks
from .version import RELEASE_VERSION


def _render_template(path: Path, values: dict[str, str]) -> str:
    result = path.read_text(encoding="utf-8")
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def _core_source(skill_root: Path) -> Path:
    runtime_core = skill_root / "templates" / "runtime" / "core"
    if runtime_core.is_dir():
        return runtime_core
    return skill_root / "templates" / "core"


def _runtime_mapping(
    *,
    skill_root: Path,
    rulers_dir: str,
    policy: dict[str, Any],
) -> dict[str, str]:
    inline_policy, policy_route = policy_blocks(policy, rulers_dir)
    values = {
        "RULERS_DIR": rulers_dir,
        "RELEASE_VERSION": RELEASE_VERSION,
        "COMMIT_POLICY_BLOCK": inline_policy,
        "COMMIT_POLICY_ROUTE": policy_route,
    }
    runtime = skill_root / "templates" / "runtime"
    mapping = {
        "AGENTS.md": _render_template(runtime / "AGENTS.md.tmpl", values),
        "INDEX.md": _render_template(runtime / "INDEX.md.tmpl", values),
        "PROJECT_PROFILE.md": _render_template(
            runtime / "PROJECT_PROFILE.md.tmpl", values
        ),
    }
    excluded_core = set()
    if policy.get("id") != "strict-cn":
        excluded_core.update({"GIT_COMMIT_CONVENTION.md", "CHANGELOG_MAINTENANCE.md"})
    for source in sorted(_core_source(skill_root).glob("*.md")):
        if source.name in excluded_core:
            continue
        mapping[f"core/{source.name}"] = _render_template(source, values)

    scripts_root = skill_root / "scripts"
    mapping["scripts/validate_rulers.py"] = (
        scripts_root / "validate_rulers.py"
    ).read_text(encoding="utf-8")
    for source in sorted((scripts_root / "rulers_lib").glob("*.py")):
        mapping[f"scripts/rulers_lib/{source.name}"] = source.read_text(encoding="utf-8")
    return mapping
