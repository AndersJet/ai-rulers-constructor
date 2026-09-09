"""Task 7: v2 Upgrade and Repair Resolution tests."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "ai-rulers-init" / "scripts"))

from rulers_lib.migration import upgrade_state_v2_to_v3
from rulers_lib.apply import (
    REPAIR_ACTIONS,
    RepairError,
    apply_repair_resolution,
    validate_repair_resolution,
)
from rulers_lib.state import SCHEMA_VERSION
from rulers_lib.version import RELEASE_VERSION


def v2_state_fixture(**overrides: Any) -> dict[str, Any]:
    """Create a schema 2 state for upgrade testing."""
    review = {
        "reviewed_by": "test-owner",
        "reviewed_at": "2026-07-20T10:00:00+08:00",
        "evidence": "test-review",
    }
    state = {
        "schema_version": 2,
        "template_version": "2.0.0",
        "rulers_dir": "documents/rulers",
        "phase": "runtime_ready",
        "policy": {"id": "strict-cn"},
        "profile": {
            "status": "reviewed",
            "content_sha256": "sha256:" + "a" * 64,
            "review": review,
        },
        "domains": {
            "core": {"level": 1, "review_status": "reviewed", "review": review},
            "backend": {
                "level": 2,
                "review_status": "reviewed",
                "target_dir": "backend",
                "required_files": ["INDEX.md"],
                "requires_active": [],
                "review": review,
            },
        },
        "managed_files": {
            "documents/rulers/core/HARD_CONSTRAINTS.md": {
                "ownership": "managed",
                "template_id": "core/HARD_CONSTRAINTS.md",
                "rendered_sha256": "sha256:" + "b" * 64,
            },
        },
    }
    state.update(overrides)
    return state


class UpgradeStateTest(unittest.TestCase):
    """v2 -> v3 state upgrade tests."""

    def test_runtime_ready_preserves_profile_domain_policy_ownership_custom_dir_and_level3(self):
        state = v2_state_fixture()
        state["rulers_dir"] = "custom/rulers"
        state["domains"]["backend"]["level3_ready"] = True
        state["domains"]["backend"]["readiness_level"] = 3
        new_state, pending = upgrade_state_v2_to_v3(state)
        self.assertEqual(new_state["schema_version"], SCHEMA_VERSION)
        self.assertEqual(new_state["template"]["version"], RELEASE_VERSION)
        self.assertNotIn("template_version", new_state)
        self.assertEqual(new_state["phase"], "runtime_ready")
        self.assertEqual(new_state["rulers_dir"], "custom/rulers")
        self.assertEqual(new_state["policy"]["id"], "strict-cn")
        self.assertEqual(new_state["profile"]["status"], "reviewed")
        self.assertEqual(new_state["profile"]["reviewed_sha256"], "sha256:" + "a" * 64)
        self.assertNotIn("content_sha256", new_state["profile"])
        self.assertEqual(new_state["domains"]["backend"]["level"], 2)
        self.assertTrue(new_state["domains"]["backend"]["level3_ready"])
        self.assertEqual(
            new_state["managed_files"]["documents/rulers/core/HARD_CONSTRAINTS.md"]["ownership"],
            "managed",
        )
        self.assertIsNone(pending)

    def test_incomplete_v2_review_downgrades_profile_and_core_but_preserves_other_fields(self):
        state = v2_state_fixture()
        state["profile"]["review"] = {"reviewed_by": "test"}  # missing evidence
        new_state, _ = upgrade_state_v2_to_v3(state)
        self.assertEqual(new_state["profile"]["status"], "draft")
        self.assertIsNone(new_state["profile"]["reviewed_sha256"])
        self.assertNotIn("review", new_state["profile"])
        self.assertEqual(new_state["domains"]["core"]["level"], 0)
        self.assertEqual(new_state["domains"]["core"]["review_status"], "draft")
        # Backend preserved
        self.assertEqual(new_state["domains"]["backend"]["level"], 2)
        self.assertEqual(new_state["policy"]["id"], "strict-cn")

    def test_incremental_pending_becomes_separate_reviewed_reconcile_plan(self):
        state = v2_state_fixture(phase="incremental_pending")
        state["pending_changes"] = {"added": [{"path": "new.md"}], "changed": [], "removed": []}
        new_state, pending = upgrade_state_v2_to_v3(state)
        self.assertEqual(new_state["phase"], "runtime_ready")
        self.assertNotIn("pending_changes", new_state)
        self.assertIsNotNone(pending)
        self.assertEqual(pending["added"], [{"path": "new.md"}])

    def test_upgrade_pending_merges_into_upgrade_plan(self):
        state = v2_state_fixture(phase="upgrade_pending")
        new_state, pending = upgrade_state_v2_to_v3(state)
        self.assertEqual(new_state["phase"], "runtime_ready")
        self.assertIsNone(pending)

    def test_repair_required_stays_repair(self):
        state = v2_state_fixture(phase="repair_required")
        new_state, _ = upgrade_state_v2_to_v3(state)
        self.assertEqual(new_state["phase"], "repair_required")


class RepairResolutionTest(unittest.TestCase):
    """Repair resolution validation and application tests."""

    def test_restore_managed_accepts_deterministic_template(self):
        state = v2_state_fixture()
        # Should not raise for managed file with template_id
        validate_repair_resolution(
            "documents/rulers/core/HARD_CONSTRAINTS.md",
            "restore-managed",
            state=state,
            project_root=Path("."),
        )

    def test_restore_managed_rejects_project_generated_without_known_bytes(self):
        state = v2_state_fixture()
        state["managed_files"]["custom.md"] = {"ownership": "project-generated"}
        with self.assertRaises(RepairError):
            validate_repair_resolution(
                "custom.md",
                "restore-managed",
                state=state,
                project_root=Path("."),
            )

    def test_adopt_current_records_hash_and_scope_downgrade(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            test_file = project / "test.md"
            test_file.write_text("adopted content")
            state = v2_state_fixture()
            state["managed_files"]["test.md"] = {
                "ownership": "managed",
                "rendered_sha256": "sha256:" + "c" * 64,
            }
            from rulers_lib.state import file_sha256
            result = apply_repair_resolution(
                "test.md",
                "adopt-current",
                state=state,
                project_root=project,
                layout=None,
            )
            self.assertEqual(
                result["managed_files"]["test.md"]["rendered_sha256"],
                file_sha256(test_file),
            )
            self.assertEqual(result["managed_files"]["test.md"]["ownership"], "collaborative")

    def test_manual_merge_requires_new_plan_over_merged_bytes(self):
        state = v2_state_fixture()
        # manual-merge should not modify state
        result = apply_repair_resolution(
            "documents/rulers/core/HARD_CONSTRAINTS.md",
            "manual-merge",
            state=state,
            project_root=Path("."),
            layout=None,
        )
        # State unchanged
        self.assertEqual(
            result["managed_files"]["documents/rulers/core/HARD_CONSTRAINTS.md"]["rendered_sha256"],
            "sha256:" + "b" * 64,
        )

    def test_unknown_action_rejected(self):
        with self.assertRaises(RepairError):
            validate_repair_resolution(
                "test.md",
                "unknown-action",
                state=None,
                project_root=Path("."),
            )

    def test_repair_actions_are_exactly_three(self):
        self.assertEqual(REPAIR_ACTIONS, {"restore-managed", "adopt-current", "manual-merge"})


if __name__ == "__main__":
    unittest.main()
