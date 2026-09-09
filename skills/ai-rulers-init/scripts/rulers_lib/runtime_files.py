"""Deterministic installation projection shared by planning and apply."""
from pathlib import Path

from .policies import load_policy
from .rendering import _runtime_mapping
from .root_entry import merge_managed_block


def runtime_files(*, skill_root, layout, policy_id, state=None):
    policy = load_policy(skill_root, policy_id)
    files = {
        f"{layout.rulers_dir}/{relative}": text.encode("utf-8")
        for relative, text in _runtime_mapping(
            skill_root=skill_root, rulers_dir=layout.rulers_dir, policy=policy,
        ).items()
    }
    profile = f"{layout.rulers_dir}/PROJECT_PROFILE.md"
    if (layout.project_root / profile).is_file():
        files.pop(profile)
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = layout.project_root / name
        if name == "CLAUDE.md" and not path.exists():
            continue
        files[name] = merge_managed_block(
            path.read_text(encoding="utf-8") if path.is_file() else "",
            layout.rulers_dir,
        ).encode("utf-8")
    if policy.get("create_changelog_if_missing") and not (layout.project_root / "CHANGELOG.md").exists():
        files["CHANGELOG.md"] = b"# Changelog\n\n## [Unreleased]\n"
    # Project-owned content is not a template upgrade target.
    inventory = (state or {}).get("managed_files") or {}
    for relative, metadata in (inventory.items() if isinstance(inventory, dict) else []):
        if not isinstance(metadata, dict):
            continue
        if metadata.get("ownership") in {"collaborative", "project-generated"} or metadata.get("project_owned"):
            files.pop(relative, None)
    return files


def retired_runtime_files(*, layout, policy_id, state=None):
    inventory = (state or {}).get("managed_files", {})
    if policy_id == "strict-cn" or not isinstance(inventory, dict):
        return set()
    return {f"{layout.rulers_dir}/core/{name}" for name in ("GIT_COMMIT_CONVENTION.md", "CHANGELOG_MAINTENANCE.md")
            if isinstance(inventory.get(f"{layout.rulers_dir}/core/{name}"), dict)
            and inventory[f"{layout.rulers_dir}/core/{name}"].get("ownership") == "managed"
            and not inventory[f"{layout.rulers_dir}/core/{name}"].get("project_owned")}
