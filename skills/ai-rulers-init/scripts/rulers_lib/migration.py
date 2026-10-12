from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import resolve_layout
from .state import file_sha256, read_state, state_json


def migrate_v1(
    *,
    skill_root: Path,
    project_root: Path,
    rulers_dir: str,
    policy_id: str,
    apply: bool,
) -> dict[str, Any]:
    layout = resolve_layout(project_root, rulers_dir)
    profile_path = layout.rulers_root / "PROJECT_PROFILE.md"
    if not profile_path.is_file():
        raise FileNotFoundError(f"Legacy PROJECT_PROFILE.md not found: {profile_path}")
    result: dict[str, Any] = {
        "mode": "legacy-v1",
        "rulers_dir": layout.rulers_dir,
        "requires_profile_review": True,
    }
    if not apply:
        return result

    # Legacy input is preserved as draft; no old prose is treated as reviewed State.
    from .plans import create_plan as unified_plan
    from .apply import apply_plan_unified
    plan = unified_plan(skill_root=skill_root, project_root=layout.project_root,
                        rulers_dir=rulers_dir, policy_id=policy_id)
    path = layout.rulers_root / ".plans" / plan["plan_id"] / "plan.json"
    summary = apply_plan_unified(path, skill_root=skill_root, project_root=layout.project_root,
                                 reviewed_by="migration-command", evidence="explicit migrate-v1 --apply; draft only")
    result["changed_files"] = summary["changed_files"]
    return result


def upgrade_state_v2_to_v3(
    state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Pure v2->v3 state conversion. Does not write files.

    Returns (new_state, pending_payload_or_None).
    """
    from .state import SCHEMA_VERSION
    from .version import RELEASE_VERSION

    import copy
    new_state = copy.deepcopy(state)
    new_state["schema_version"] = SCHEMA_VERSION
    new_state.pop("template_version", None)
    new_state.setdefault("template", {})["version"] = RELEASE_VERSION

    phase = new_state.get("phase", "runtime_ready")
    pending_payload = None

    if phase == "incremental_pending":
        pending_payload = new_state.pop("pending_changes", None)
        new_state["phase"] = "runtime_ready"
    elif phase == "upgrade_pending":
        new_state["phase"] = "runtime_ready"

    profile = new_state.get("profile") or {}
    if isinstance(profile, dict):
        review = profile.get("review") or {}
        has_complete_review = (
            isinstance(review, dict)
            and review.get("reviewed_by")
            and review.get("evidence")
            and review.get("reviewed_at")
        )
        if has_complete_review:
            profile["reviewed_sha256"] = profile.pop("content_sha256", None)
            profile["status"] = "reviewed"
        else:
            profile.pop("content_sha256", None)
            profile["reviewed_sha256"] = None
            profile["status"] = "draft"
            profile.pop("review", None)
            domains = new_state.get("domains") or {}
            core = domains.get("core")
            if isinstance(core, dict):
                core["level"] = 0
                core["review_status"] = "draft"
                core.pop("review", None)
        new_state["profile"] = profile

    new_state.pop("pending_changes", None)
    return new_state, pending_payload
