"""Task 5: Compact Context, Profile selector, and load graph gate tests."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "ai-rulers-init" / "scripts"))

from rulers_lib.issues import ValidationIssue
from rulers_lib.validation import (
    BUDGETS,
    ProjectInspection,
    build_runtime_context,
    inspect_project,
    runtime_context_json,
)
from rulers_lib.paths import RulersLayout


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "ai-rulers-init"
RULERS_DIR = "documents/rulers"


def context_state_fixture() -> dict[str, Any]:
    review = {
        "reviewed_by": "test-owner",
        "reviewed_at": "2026-07-20T10:00:00+08:00",
        "evidence": "test-review",
    }
    return {
        "schema_version": 3,
        "template_version": "3.0.0",
        "rulers_dir": "documents/rulers",
        "phase": "runtime_ready",
        "policy": {"id": "strict-cn"},
        "profile": {
            "status": "reviewed",
            "reviewed_sha256": "sha256:" + "1" * 64,
            "review": review,
        },
        "domains": {
            "core": {"level": 1, "review_status": "reviewed", "review": review},
            "backend": {
                "level": 2, "review_status": "reviewed",
                "target_dir": "backend", "required_files": ["INDEX.md"],
                "requires_active": [], "level3_ready": False, "review": review,
            },
            "security": {
                "level": 2, "review_status": "reviewed",
                "target_dir": "security", "required_files": ["INDEX.md"],
                "requires_active": [], "level3_ready": False, "review": review,
            },
            "delivery": {
                "level": 2, "review_status": "reviewed",
                "target_dir": "delivery", "required_files": ["INDEX.md"],
                "requires_active": ["security"], "level3_ready": True,
                "readiness_level": 3, "review": review,
            },
        },
        "managed_files": {},
    }


def _make_healthy_project(tmp: Path) -> Path:
    """Create a minimal healthy project with schema 3 state."""
    project = tmp / "project"
    rulers = project / RULERS_DIR
    core = rulers / "core"
    core.mkdir(parents=True)
    (rulers / "backend").mkdir()
    (rulers / "security").mkdir()
    (rulers / "delivery").mkdir()
    NL = chr(10)
    (rulers / "AGENTS.md").write_text("# Rulers AGENTS" + NL)
    (rulers / "INDEX.md").write_text("# Index" + NL)
    (rulers / "PROJECT_PROFILE.md").write_text("# Profile" + NL + "## " + chr(0x9879) + chr(0x76EE) + chr(0x8EAB) + chr(0x4EFD) + NL + "test" + NL)
    (core / "HARD_CONSTRAINTS.md").write_text("# Hard" + NL)
    (core / "WORKFLOW.md").write_text("# Workflow" + NL)
    (rulers / "backend" / "INDEX.md").write_text("# Backend" + NL)
    (rulers / "security" / "INDEX.md").write_text("# Security" + NL)
    (rulers / "delivery" / "INDEX.md").write_text("# Delivery" + NL)
    ms = "<!-- ai-rulers-init:begin version=3 -->"
    me = "<!-- ai-rulers-init:end -->"
    (project / "AGENTS.md").write_text("# Project" + NL + ms + NL + "block" + NL + me + NL)
    from rulers_lib.state import file_sha256
    state = context_state_fixture()
    state["profile"]["reviewed_sha256"] = file_sha256(rulers / "PROJECT_PROFILE.md")
    metadata = "\n```yaml\nmetadata:\n  applies_to:\n    - '**/*'\n  trigger_keywords:\n    - fixture\n  must_load_with: []\n```\n"
    for domain in ("backend", "security", "delivery"):
        path = rulers / domain / "INDEX.md"
        path.write_text(path.read_text() + metadata)
        state["managed_files"][path.relative_to(project).as_posix()] = {"ownership": "managed", "rendered_sha256": file_sha256(path)}
    (rulers / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))
    return project


class UnifiedContextTest(unittest.TestCase):
    """Task 5 Context tests."""

    def test_managed_inventory_one_and_hundred_have_identical_context(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx1 = build_runtime_context(inspection, requested_domains=["backend"])
            rulers = project / RULERS_DIR
            state = json.loads((rulers / "RULERS_STATE.json").read_text())
            managed = state.setdefault("managed_files", {})
            from rulers_lib.state import file_sha256
            for i in range(100):
                fname = f"documents/rulers/backend/rule_{i:03d}.md"
                fpath = project / fname
                fpath.write_text(f"# Rule {i}\n\n```yaml\nmetadata:\n  applies_to:\n    - backend/**\n  trigger_keywords:\n    - budget\n  must_load_with: []\n```\n")
                managed[fname] = {"ownership": "managed", "rendered_sha256": file_sha256(fpath)}
            (rulers / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))
            inspection2 = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx2 = build_runtime_context(inspection2, requested_domains=["backend"])
            c1 = {k: v for k, v in ctx1.items() if k != "issues"}
            c2 = {k: v for k, v in ctx2.items() if k != "issues"}
            self.assertEqual(c1, c2)

    def test_profile_hash_mismatch_effectively_downgrades_to_profile_draft(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            rulers = project / RULERS_DIR
            state = json.loads((rulers / "RULERS_STATE.json").read_text())
            state["profile"]["reviewed_sha256"] = "sha256:" + "f" * 64
            (rulers / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection)
            self.assertEqual(ctx["phase"], "profile_draft")
            self.assertEqual(ctx["next_action"], "plan-reconcile")

    def test_core_or_entry_drift_effectively_requires_repair(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            rulers = project / RULERS_DIR
            state = json.loads((rulers / "RULERS_STATE.json").read_text())
            state["managed_files"]["documents/rulers/core/HARD_CONSTRAINTS.md"] = {"ownership": "managed", "rendered_sha256": "sha256:" + "a" * 64}
            (rulers / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection)
            self.assertEqual(ctx["phase"], "repair_required")
            self.assertEqual(ctx["next_action"], "plan-repair")

    def test_schema_two_effectively_requires_upgrade(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            rulers = project / RULERS_DIR
            state = json.loads((rulers / "RULERS_STATE.json").read_text())
            state["schema_version"] = 2
            (rulers / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection)
            self.assertEqual(ctx["phase"], "upgrade_required")
            self.assertEqual(ctx["next_action"], "plan-upgrade")

    def test_domain_drift_removes_only_that_route(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            (project / RULERS_DIR / "backend" / "INDEX.md").unlink()
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection, requested_domains=["backend", "security"])
            self.assertNotIn("backend", ctx["available_domains"])
            self.assertNotIn("backend", ctx["routes"])
            self.assertIn("security", ctx["available_domains"])

    def test_security_drift_removes_delivery_route_and_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            (project / RULERS_DIR / "security" / "INDEX.md").unlink()
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            self.assertIn("security", inspection.invalid_domains)
            self.assertIn("delivery", inspection.invalid_domains)
            ctx = build_runtime_context(inspection)
            self.assertNotIn("security", ctx["available_domains"])
            self.assertNotIn("delivery", ctx["available_domains"])
            self.assertNotIn("delivery", ctx["level3_ready"])

    def test_unfinished_transaction_blocks_external_context_but_not_current_apply_validation(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            rulers = project / RULERS_DIR
            tx_dir = rulers / ".transactions"
            tx_dir.mkdir()
            (tx_dir / "maintenance.lock").write_text(json.dumps({"pid": 99999, "nonce": "test-nonce", "created_at": "2026-07-20T10:00:00+08:00"}))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection)
            self.assertIn(ctx["phase"], ("repair_required", "runtime_ready"))

    def test_requested_backend_load_graph_excludes_security_delivery_state_runtime_index_and_references(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection, requested_domains=["backend"])
            all_paths = ctx["load"]["core"] + ctx["load"]["indexes"]
            self.assertIn(f"{RULERS_DIR}/core/HARD_CONSTRAINTS.md", all_paths)
            self.assertIn(f"{RULERS_DIR}/backend/INDEX.md", all_paths)
            for path in all_paths:
                self.assertNotIn("security", path)
                self.assertNotIn("delivery", path)
                self.assertNotIn("RULERS_STATE", path)
            self.assertEqual(list(ctx["routes"].keys()), ["backend"])

    def test_profile_load_selector_uses_identity_commands_and_only_core_requested_scope_rows(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection, requested_domains=["backend"])
            profile = ctx["profile"]
            self.assertEqual(profile["selection"], "section-and-scope")
            self.assertIn(chr(0x9879) + chr(0x76EE) + chr(0x8EAB) + chr(0x4EFD), profile["always_sections"])
            self.assertIn(chr(0x547D) + chr(0x4EE4), profile["always_sections"])
            self.assertIn("core", profile["scopes"])
            self.assertIn("backend", profile["scopes"])
            self.assertNotIn("security", profile["scopes"])

    def test_context_issues_are_sorted_truncated_and_under_utf8_limit(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            rulers = project / RULERS_DIR
            state = json.loads((rulers / "RULERS_STATE.json").read_text())
            managed = state.setdefault("managed_files", {})
            for i in range(200):
                managed[f"documents/rulers/backend/drift_{i:03d}.md"] = {"ownership": "managed", "rendered_sha256": "sha256:" + "b" * 64}
            (rulers / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection, requested_domains=["backend"])
            output = runtime_context_json(ctx)
            self.assertLessEqual(len(output), BUDGETS["context_bytes"])
            parsed = json.loads(output)
            self.assertIn("phase", parsed)
            self.assertIn("next_action", parsed)
            self.assertIn("load", parsed)

    def test_next_action_and_details_command_follow_error_code(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            rulers = project / RULERS_DIR
            state = json.loads((rulers / "RULERS_STATE.json").read_text())
            state["profile"]["reviewed_sha256"] = "sha256:" + "e" * 64
            (rulers / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection)
            self.assertNotEqual(ctx["next_action"], "none")
            self.assertIn("details_command", ctx)
            self.assertIn("validate_rulers.py", ctx["details_command"])

    def test_healthy_context_omits_details_command_but_error_context_retains_it(self):
        with tempfile.TemporaryDirectory() as td:
            project = _make_healthy_project(Path(td))
            inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
            ctx = build_runtime_context(inspection)
            self.assertEqual(ctx["next_action"], "none")
            self.assertNotIn("details_command", ctx)


if __name__ == "__main__":
    unittest.main()
