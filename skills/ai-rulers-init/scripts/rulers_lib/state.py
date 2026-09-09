from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, Mapping

from .domains import load_domain_registry
from .issues import ValidationIssue
from .version import RELEASE_VERSION


SCHEMA_VERSION = 3


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "uninitialized": {"planned"},
    "planned": {"profile_draft", "repair_required"},
    "profile_draft": {"profile_reviewed", "repair_required"},
    "profile_reviewed": {"rules_candidate", "runtime_ready", "repair_required"},
    "rules_candidate": {"runtime_ready", "repair_required"},
    "runtime_ready": {"repair_required"},
    "repair_required": {
        "planned", "profile_draft", "profile_reviewed", "rules_candidate", "runtime_ready"
    },
}


class StateTransitionError(ValueError):
    pass


def classify_state_schema(
    state: Mapping[str, Any], *, target_version: int = 3
) -> Literal["current", "upgrade", "unsupported"]:
    schema_version = state.get("schema_version")
    if type(schema_version) is not int or type(target_version) is not int:
        return "unsupported"
    if schema_version == target_version:
        return "current"
    if schema_version == 2 and target_version == 3:
        return "upgrade"
    return "unsupported"


def _domain_state(
    *,
    detected: bool,
    config: Mapping[str, Any],
    generated: bool = False,
) -> dict[str, Any]:
    result = {
        "detected": detected,
        "generated": generated,
        "review_status": "draft" if generated else "not_started",
        "level": 0,
        "review": {
            "reviewed_by": None,
            "reviewed_at": None,
            "evidence": None,
        },
        "target_dir": config["target_dir"],
        "required_files": list(config["templates"]),
        "requires_active": list(config["requires_active"]),
    }
    return result


def create_initial_state(
    *,
    rulers_dir: str,
    policy_id: str,
    detected_domains: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    registry = load_domain_registry(Path(__file__).resolve().parents[2])
    detected = set(detected_domains)
    unknown = sorted(detected - registry.keys())
    if unknown:
        raise ValueError("Unknown detected domain: " + ", ".join(unknown))
    domains: dict[str, Any] = {
        "core": _domain_state(
            detected=True,
            generated=True,
            config=registry["core"],
        )
    }
    for domain in sorted(detected - {"core"}):
        domains[domain] = _domain_state(
            detected=True,
            config=registry[domain],
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "template": {"version": RELEASE_VERSION},
        "rulers_dir": rulers_dir,
        "phase": "planned",
        "policy": {"id": policy_id},
        "profile": {
            "status": "draft",
            "content_sha256": None,
            "review": {
                "reviewed_by": None,
                "reviewed_at": None,
                "evidence": None,
            },
        },
        "domains": domains,
        "managed_files": {},
        "last_operation": {
            "kind": "init",
            "status": "in_progress",
            "updated_at": None,
        },
    }


def transition_state(state: dict[str, Any], target_phase: str) -> dict[str, Any]:
    current = state.get("phase", "uninitialized")
    if target_phase == current:
        return copy.deepcopy(state)
    if target_phase not in ALLOWED_TRANSITIONS.get(current, set()):
        raise StateTransitionError(f"Illegal state transition: {current} -> {target_phase}")
    result = copy.deepcopy(state)
    result["phase"] = target_phase
    return result


def review_profile(
    state: dict[str, Any],
    *,
    reviewed_by: str,
    reviewed_at: str,
    evidence: str,
    content_sha256: str | None = None,
) -> dict[str, Any]:
    if not reviewed_by.strip() or not evidence.strip():
        raise ValueError("Profile review requires reviewer identity and review evidence.")
    if state.get("phase") != "profile_draft":
        raise StateTransitionError(
            f"Profile review requires profile_draft phase, got {state.get('phase')}"
        )
    result = transition_state(state, "profile_reviewed")
    review = {
        "reviewed_by": reviewed_by.strip(),
        "reviewed_at": reviewed_at,
        "evidence": evidence.strip(),
    }
    result["profile"]["status"] = "reviewed"
    result["profile"]["review"] = review
    if content_sha256 is not None:
        result["profile"]["reviewed_sha256"] = content_sha256
        result["profile"]["content_sha256"] = content_sha256
    core = result["domains"]["core"]
    core["level"] = 1
    core["review_status"] = "reviewed"
    core["review"] = copy.deepcopy(review)
    result["last_operation"] = {
        "kind": "review-profile",
        "status": "complete",
        "updated_at": reviewed_at,
    }
    return result


def mark_runtime_ready(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("profile", {}).get("status") != "reviewed":
        raise StateTransitionError("Runtime readiness requires a reviewed profile.")
    result = copy.deepcopy(state)
    if result.get("phase") == "profile_reviewed":
        result = transition_state(result, "rules_candidate")
    if result.get("phase") != "rules_candidate":
        raise StateTransitionError(
            f"Runtime readiness requires rules_candidate phase, got {result.get('phase')}"
        )
    validation_issues = validate_state(result)
    blocking = [issue for issue in validation_issues if issue.severity == "error"]
    if blocking:
        raise StateTransitionError(
            "State is not ready for runtime: "
            + "; ".join(f"{issue.code} {issue.message}" for issue in blocking)
        )
    result = transition_state(result, "runtime_ready")
    result["last_operation"] = {
        "kind": "mark-runtime-ready",
        "status": "complete",
        "updated_at": result.get("profile", {}).get("review", {}).get("reviewed_at"),
    }
    return result


def validate_state(state: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    def error(code, message, scope="core"):
        issues.append(ValidationIssue(code, message, "RULERS_STATE.json", scope=scope))
    def reviewed(value):
        return isinstance(value, Mapping) and all(
            isinstance(value.get(key), str) and value[key].strip()
            for key in ("reviewed_by", "reviewed_at", "evidence")
        )
    if state.get("schema_version") != SCHEMA_VERSION:
        error("VR010", "Unsupported or missing RULERS_STATE schema version.")
    if not all(isinstance(state.get(key), dict) for key in ("profile", "domains", "managed_files", "policy")):
        error("VR010", "State profile, domains, policy and managed_files must be objects.")
        if not isinstance(state.get("profile"), dict) or not isinstance(state.get("domains"), dict):
            return issues
    profile, domains = state["profile"], state["domains"]
    core = domains.get("core")
    if not isinstance(core, dict):
        error("VR011", "State must contain core.")
        return issues
    if profile.get("status") not in {"draft", "reviewed", "legacy_review_required"}:
        error("VR011", "Unknown profile status.")
    if profile.get("status") == "reviewed" and not reviewed(profile.get("review")):
        error("VR014", "Profile review evidence is incomplete.")
    if state.get("phase") == "runtime_ready" and profile.get("status") != "reviewed":
        error("VR012", "Runtime-ready rulers require a reviewed profile.")
    for domain, value in domains.items():
        if not isinstance(value, dict) or type(value.get("level")) is not int or not 0 <= value["level"] <= 3:
            error("VR013", f"Invalid domain state: {domain}")
            continue
        level = value["level"]
        if domain == "core" and profile.get("status") != "reviewed" and level > 0:
            error("VR011", "An unreviewed profile cannot activate Core.")
        if level >= (1 if domain == "core" else 2):
            if value.get("review_status") != "reviewed":
                error("VR013", f"Domain '{domain}' has no review.", domain)
            if not reviewed(value.get("review")):
                error("VR014", f"Domain '{domain}' review evidence is incomplete.", domain)
        if value.get("level3_ready") and (value.get("readiness_level") != 3 or level < 2 or value.get("review_status") != "reviewed" or not reviewed(value.get("review"))):
            error("VR015", f"Domain '{domain}' has inconsistent Level 3 readiness.", domain)
        requirements = value.get("requires_active", [])
        if not isinstance(requirements, list) or any(not isinstance(d, str) for d in requirements):
            error("VR016", "Invalid domain dependencies.", domain)
            continue
        if domain == "delivery":
            requirements = list(set(requirements) | {"security"})
        if level >= 2 or value.get("level3_ready"):
            for dependency in requirements:
                other = domains.get(dependency, {})
                if not isinstance(other, dict) or other.get("level", 0) < 2 or other.get("review_status") != "reviewed":
                    error("VR016", f"Domain '{domain}' requires active '{dependency}'.", domain)
    return issues


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def state_json(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
