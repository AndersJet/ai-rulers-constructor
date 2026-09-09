from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-rulers-init"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))


class RulersStateMachineTest(unittest.TestCase):
    def test_schema_two_is_classified_as_upgrade_not_corruption(self) -> None:
        from rulers_lib.state import classify_state_schema

        self.assertEqual("upgrade", classify_state_schema({"schema_version": 2}))
        self.assertEqual("current", classify_state_schema({"schema_version": 3}))
        for schema_version in (None, "2", 1, 4):
            with self.subTest(schema_version=schema_version):
                self.assertEqual(
                    "unsupported",
                    classify_state_schema({"schema_version": schema_version}),
                )

    def test_v2_migration_fixtures_are_complete_independent_states(self) -> None:
        fixture_dir = ROOT / "tests" / "fixtures" / "ai-rulers-v2"
        fixture_paths = {
            phase: fixture_dir / f"schema2_{phase}.json"
            for phase in ("runtime_ready", "incremental_pending")
        }
        for path in fixture_paths.values():
            self.assertTrue(path.is_file(), f"missing fixture: {path}")

        states = {
            phase: json.loads(path.read_text(encoding="utf-8"))
            for phase, path in fixture_paths.items()
        }
        required = {
            "schema_version",
            "template_version",
            "rulers_dir",
            "phase",
            "policy",
            "profile",
            "domains",
            "managed_files",
            "last_operation",
        }
        hash_pattern = re.compile(r"^sha256:[0-9a-f]{64}$")

        def assert_hashes(value: object) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.endswith("sha256"):
                        self.assertIsInstance(item, str)
                        self.assertRegex(item, hash_pattern)
                    assert_hashes(item)
            elif isinstance(value, list):
                for item in value:
                    assert_hashes(item)

        for phase, state in states.items():
            self.assertTrue(required.issubset(state))
            self.assertEqual(2, state["schema_version"])
            self.assertEqual("documents/custom-rulers", state["rulers_dir"])
            self.assertEqual(phase, state["phase"])
            self.assertEqual("reviewed", state["profile"]["status"])
            self.assertTrue(state["profile"]["review"]["evidence"])
            for domain in ("core", "backend", "security", "delivery"):
                review = state["domains"][domain]["review"]
                self.assertEqual("reviewed", state["domains"][domain]["review_status"])
                self.assertTrue(review["reviewed_by"])
                self.assertTrue(review["reviewed_at"])
                self.assertTrue(review["evidence"])
            delivery = state["domains"]["delivery"]
            self.assertEqual(3, delivery["readiness_level"])
            self.assertTrue(delivery["level3_ready"])
            assert_hashes(state)

        runtime = states["runtime_ready"]
        managed = runtime["managed_files"]
        core = managed["documents/custom-rulers/core/HARD_CONSTRAINTS.md"]
        backend = managed["documents/custom-rulers/backend/INDEX.md"]
        self.assertEqual("managed", core["ownership"])
        self.assertEqual("core/HARD_CONSTRAINTS.md", core["template_id"])
        self.assertEqual("project-generated", backend["ownership"])
        self.assertNotIn("template_id", backend)
        self.assertNotIn("source_sha256", backend)

        incremental = states["incremental_pending"]
        pending = incremental["pending_changes"]
        self.assertTrue(pending["added"])
        self.assertTrue(pending["changed"])
        self.assertTrue(pending["removed"])
        before = dict(runtime)
        after = dict(incremental)
        before.pop("phase")
        after.pop("phase")
        after.pop("pending_changes")
        self.assertEqual(before, after)

    def test_shared_support_materializes_real_hashes_and_snapshots_files(self) -> None:
        from tests.ai_rulers_test_support import (
            materialize_v2_fixture,
            read_state,
            snapshot_project,
            write_profile,
        )
        from rulers_lib.state import file_sha256

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            profile = write_profile(
                project,
                [("Python runtime", "observed", "pyproject.toml", "core", "high")],
                unresolved=[("Owner approval", "activation gate", "backend", "owner")],
                rulers_dir="documents/custom-rulers",
            )
            self.assertIn(
                "| Python runtime | observed | pyproject.toml | core | high |",
                profile.read_text(encoding="utf-8"),
            )

            state_path, state = materialize_v2_fixture(
                project,
                "schema2_runtime_ready.json",
            )
            rulers = project / "documents" / "custom-rulers"
            self.assertEqual(state, read_state(project, "documents/custom-rulers"))
            self.assertEqual(file_sha256(rulers / "PROJECT_PROFILE.md"), state["profile"]["content_sha256"])
            for relative in (
                "documents/custom-rulers/PROJECT_PROFILE.md",
                "documents/custom-rulers/core/HARD_CONSTRAINTS.md",
                "documents/custom-rulers/backend/INDEX.md",
            ):
                current_hash = file_sha256(project / relative)
                metadata = state["managed_files"][relative]
                self.assertEqual(
                    current_hash,
                    metadata["rendered_sha256"],
                )
                if relative.endswith("backend/INDEX.md"):
                    self.assertNotIn("source_sha256", metadata)
                    self.assertNotIn("template_id", metadata)
                else:
                    self.assertEqual(current_hash, metadata["source_sha256"])
            self.assertEqual(rulers / "RULERS_STATE.json", state_path)

            (project / ".plans").mkdir()
            (project / ".plans" / "plan.json").write_text("{}", encoding="utf-8")
            (project / ".transactions").mkdir()
            (project / ".transactions" / "journal.json").write_text("{}", encoding="utf-8")
            nested_plan = project / "nested" / ".plans" / "keep.txt"
            nested_plan.parent.mkdir(parents=True)
            nested_plan.write_bytes(b"nested plan bytes")
            nested_transaction = project / "src" / ".transactions" / "keep.txt"
            nested_transaction.parent.mkdir(parents=True)
            nested_transaction.write_bytes(b"nested transaction bytes")
            snapshot = snapshot_project(project)
            self.assertIn("documents/custom-rulers/RULERS_STATE.json", snapshot)
            self.assertFalse(any(path.startswith(".plans/") for path in snapshot))
            self.assertFalse(any(path.startswith(".transactions/") for path in snapshot))
            self.assertIn("nested/.plans/keep.txt", snapshot)
            self.assertEqual(
                (b"nested plan bytes", nested_plan.stat().st_mtime_ns),
                snapshot["nested/.plans/keep.txt"],
            )
            self.assertIn("src/.transactions/keep.txt", snapshot)

    def test_new_state_keeps_draft_profile_and_core_at_level_zero(self) -> None:
        from rulers_lib.state import create_initial_state

        state = create_initial_state(
            rulers_dir="documents/coding-standards",
            policy_id="strict-cn",
            detected_domains=["backend"],
        )

        self.assertEqual("planned", state["phase"])
        self.assertEqual("draft", state["profile"]["status"])
        self.assertEqual(0, state["domains"]["core"]["level"])
        self.assertEqual("draft", state["domains"]["core"]["review_status"])

    def test_illegal_state_transition_is_rejected(self) -> None:
        from rulers_lib.state import StateTransitionError, transition_state

        state = {
            "schema_version": 2,
            "phase": "profile_draft",
            "profile": {"status": "draft"},
            "domains": {"core": {"level": 0, "review_status": "draft"}},
        }

        with self.assertRaises(StateTransitionError):
            transition_state(state, "runtime_ready")

    def test_draft_profile_cannot_activate_core(self) -> None:
        from rulers_lib.state import validate_state

        state = {
            "schema_version": 2,
            "template_version": "2.0.0",
            "rulers_dir": "documents/rulers",
            "phase": "profile_draft",
            "profile": {"status": "draft", "review": {}},
            "domains": {
                "core": {
                    "detected": True,
                    "generated": True,
                    "review_status": "draft",
                    "level": 1,
                }
            },
            "managed_files": {},
        }

        codes = {issue.code for issue in validate_state(state)}

        self.assertIn("VR011", codes)

    def test_reviewing_profile_records_evidence_and_activates_core_level_one(self) -> None:
        from rulers_lib.state import create_initial_state, review_profile, transition_state

        state = create_initial_state(
            rulers_dir="documents/rulers",
            policy_id="strict-cn",
        )
        state = transition_state(state, "profile_draft")

        reviewed = review_profile(
            state,
            reviewed_by="project-owner",
            reviewed_at="2026-07-10T12:00:00+08:00",
            evidence="conversation-approval",
        )

        self.assertEqual("profile_reviewed", reviewed["phase"])
        self.assertEqual("reviewed", reviewed["profile"]["status"])
        self.assertEqual(1, reviewed["domains"]["core"]["level"])
        self.assertEqual(
            "project-owner",
            reviewed["profile"]["review"]["reviewed_by"],
        )

    def test_level3_readiness_requires_reviewed_level_two_domain_and_security(self) -> None:
        from rulers_lib.state import validate_state

        state = {
            "schema_version": 2,
            "template_version": "2.0.0",
            "rulers_dir": "documents/rulers",
            "phase": "rules_candidate",
            "profile": {"status": "reviewed", "review": {"reviewed_by": "owner"}},
            "domains": {
                "core": {"level": 1, "review_status": "reviewed", "review": {"reviewed_by": "owner"}},
                "security": {"level": 0, "review_status": "draft", "review": {}},
                "delivery": {
                    "level": 1,
                    "review_status": "draft",
                    "readiness_level": 3,
                    "level3_ready": True,
                    "review": {},
                },
            },
            "managed_files": {},
        }

        codes = {issue.code for issue in validate_state(state)}

        self.assertIn("VR015", codes)
        self.assertIn("VR016", codes)


class RulersPathTest(unittest.TestCase):
    def test_safe_child_rejects_parent_absolute_and_symlink_escape(self) -> None:
        from rulers_lib.paths import UnsafeRulersPathError, resolve_safe_child

        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside:
            root = Path(temp_dir)
            (root / "inside").mkdir()
            (root / "inside" / "link").symlink_to(Path(outside), target_is_directory=True)

            self.assertEqual(
                (root / "inside" / "child.txt").resolve(),
                resolve_safe_child(root, "inside/child.txt"),
            )
            for candidate in ("../outside.txt", Path(outside), "inside/link/escaped.txt"):
                with self.subTest(candidate=candidate):
                    with self.assertRaises(UnsafeRulersPathError):
                        resolve_safe_child(root, candidate)

    def test_custom_rulers_directory_is_resolved_from_project_root(self) -> None:
        from rulers_lib.paths import resolve_layout

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir).resolve()
            layout = resolve_layout(project_root, "docs/ai/coding-standards")

        self.assertEqual(project_root, layout.project_root)
        self.assertEqual(
            project_root / "docs" / "ai" / "coding-standards",
            layout.rulers_root,
        )

    def test_rulers_directory_cannot_escape_project_root(self) -> None:
        from rulers_lib.paths import UnsafeRulersPathError, resolve_layout

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(UnsafeRulersPathError):
                resolve_layout(Path(temp_dir), "../outside")

    def test_symlinked_rulers_directory_cannot_escape_project_root(self) -> None:
        from rulers_lib.paths import UnsafeRulersPathError, resolve_layout

        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside:
            project = Path(temp_dir)
            (project / "documents").mkdir()
            (project / "documents" / "rulers").symlink_to(Path(outside), target_is_directory=True)

            with self.assertRaises(UnsafeRulersPathError):
                resolve_layout(project, "documents/rulers")

    def test_rulers_directory_cannot_be_project_root(self) -> None:
        from rulers_lib.paths import UnsafeRulersPathError, resolve_layout

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(UnsafeRulersPathError):
                resolve_layout(Path(temp_dir), ".")


class RootEntryMergeTest(unittest.TestCase):
    def test_parser_recognizes_exactly_one_v2_or_v3_block(self) -> None:
        from rulers_lib.root_entry import find_managed_blocks

        for version in (2, 3):
            with self.subTest(version=version):
                text = f"""before
<!-- ai-rulers-init:begin version={version} -->
managed
<!-- ai-rulers-init:end -->
after
"""
                blocks = find_managed_blocks(text)

                self.assertEqual(1, len(blocks))
                self.assertEqual(str(version), blocks[0].group("version"))

    def test_parser_rejects_multiple_mixed_version_blocks(self) -> None:
        from rulers_lib.root_entry import (
            RootEntryConflictError,
            find_managed_blocks,
            has_valid_managed_block,
            merge_managed_block,
        )

        v2 = """<!-- ai-rulers-init:begin version=2 -->
v2
<!-- ai-rulers-init:end -->
"""
        v3 = """<!-- ai-rulers-init:begin version=3 -->
v3
<!-- ai-rulers-init:end -->
"""
        with self.assertRaises(RootEntryConflictError):
            merge_managed_block(v2 + v3, "documents/rulers")

        malformed = {
            "nested": """<!-- ai-rulers-init:begin version=2 -->
<!-- ai-rulers-init:begin version=3 -->
managed
<!-- ai-rulers-init:end -->
""",
            "unknown-complete": """<!-- ai-rulers-init:begin version=4 -->
managed
<!-- ai-rulers-init:end -->
""",
            "unknown-orphan": "<!-- ai-rulers-init:begin version=4 -->\n",
            "orphan-end": "<!-- ai-rulers-init:end -->\n",
            "truncated-begin": "<!-- ai-rulers-init:begin version=2",
            "valid-plus-truncated": v2 + "<!-- ai-rulers-init:begin version=3",
            "truncated-end": "<!-- ai-rulers-init:end",
            "long-unclosed": "<!-- ai-rulers-init:begin version=2 -->\n" * 2048,
        }
        self.assertEqual((), find_managed_blocks(malformed["nested"]))
        self.assertEqual((), find_managed_blocks(malformed["long-unclosed"]))
        for case, text in malformed.items():
            with self.subTest(case=case):
                with self.assertRaises(RootEntryConflictError):
                    merge_managed_block(text, "documents/rulers")
                self.assertFalse(has_valid_managed_block(text))

        replaced = merge_managed_block("before\n" + v3 + "after\n", "documents/rulers")
        self.assertTrue(replaced.startswith("before\n"))
        self.assertTrue(replaced.endswith("after\n"))
        self.assertEqual(1, replaced.count("<!-- ai-rulers-init:begin -->"))
        self.assertNotIn("version=3", replaced)
        self.assertNotIn("version=2", replaced)

    def test_managed_block_preserves_existing_agents_content_and_is_idempotent(self) -> None:
        from rulers_lib.root_entry import merge_managed_block

        original = "# Existing instructions\n\nPreserve this paragraph.\n"
        once = merge_managed_block(original, "documents/rulers")
        twice = merge_managed_block(once, "documents/rulers")

        self.assertIn("Preserve this paragraph.", once)
        self.assertIn("<!-- ai-rulers-init:begin -->", once)
        self.assertEqual(once, twice)

    def test_duplicate_managed_blocks_are_rejected(self) -> None:
        from rulers_lib.root_entry import RootEntryConflictError, merge_managed_block

        block = """<!-- ai-rulers-init:begin version=2 -->
managed
<!-- ai-rulers-init:end -->
"""
        with self.assertRaises(RootEntryConflictError):
            merge_managed_block(block + block, "documents/rulers")


class PolicyAndDomainRegistryTest(unittest.TestCase):
    def test_security_invalidation_expands_to_delivery(self) -> None:
        from rulers_lib.domains import expand_reverse_dependencies, load_domain_registry
        from rulers_lib.state import create_initial_state

        registry = load_domain_registry(SKILL_ROOT)

        self.assertTrue(all("requires_active" in config for config in registry.values()))
        self.assertEqual(["security"], registry["delivery"]["requires_active"])
        self.assertEqual(
            frozenset({"security", "delivery"}),
            expand_reverse_dependencies({"security"}, registry),
        )
        self.assertEqual(
            frozenset({"backend"}),
            expand_reverse_dependencies({"backend"}, registry),
        )
        transitive_registry = {
            "security": {"requires_active": []},
            "delivery": {"requires_active": ["security"]},
            "release": {"requires_active": ["delivery"]},
            "frontend": {"requires_active": []},
        }
        self.assertEqual(
            frozenset({"security", "delivery", "release"}),
            expand_reverse_dependencies({"security"}, transitive_registry),
        )
        cycle_registry = {
            "security": {"requires_active": ["delivery"]},
            "delivery": {"requires_active": ["security"]},
        }
        self.assertEqual(
            frozenset({"security", "delivery"}),
            expand_reverse_dependencies({"security"}, cycle_registry),
        )
        invalid_registries = {
            "missing": {"backend": {}},
            "string": {
                "backend": {"requires_active": "security"},
                "security": {"requires_active": []},
            },
            "none": {"backend": {"requires_active": None}},
            "non-sequence": {"backend": {"requires_active": 1}},
            "non-string-item": {"backend": {"requires_active": [1]}},
            "unknown-reference": {
                "backend": {"requires_active": ["missing-domain"]},
            },
        }
        for case, invalid_registry in invalid_registries.items():
            with self.subTest(case=case):
                with self.assertRaisesRegex(ValueError, r"backend.*requires_active"):
                    expand_reverse_dependencies({"backend"}, invalid_registry)

        state = create_initial_state(
            rulers_dir="documents/rulers",
            policy_id="strict-cn",
            detected_domains=["delivery"],
        )
        for domain in ("core", "delivery"):
            self.assertEqual(
                registry[domain]["target_dir"],
                state["domains"][domain]["target_dir"],
            )
            self.assertEqual(
                registry[domain]["templates"],
                state["domains"][domain]["required_files"],
            )
            self.assertEqual(
                registry[domain]["requires_active"],
                state["domains"][domain]["requires_active"],
            )
        with self.assertRaisesRegex(ValueError, "unknown-domain"):
            create_initial_state(
                rulers_dir="documents/rulers",
                policy_id="strict-cn",
                detected_domains=["unknown-domain"],
            )

    def test_policy_profiles_keep_strict_cn_and_project_native_distinct(self) -> None:
        from rulers_lib.policies import load_policy

        strict_cn = load_policy(SKILL_ROOT, "strict-cn")
        project_native = load_policy(SKILL_ROOT, "project-native")

        self.assertEqual("zh-CN", strict_cn["commit_language"])
        self.assertTrue(strict_cn["create_changelog_if_missing"])
        self.assertIsNone(project_native["commit_language"])
        self.assertFalse(project_native["create_changelog_if_missing"])

    def test_registry_contains_security_and_delivery_capabilities(self) -> None:
        from rulers_lib.domains import load_domain_registry

        registry = load_domain_registry(SKILL_ROOT)

        self.assertIn("security", registry)
        self.assertIn("delivery", registry)
        self.assertEqual(3, registry["delivery"]["readiness_level"])
        self.assertIn("ROLLBACK.md", registry["delivery"]["templates"])


class TemplateValidationTest(unittest.TestCase):
    def test_current_v2_skill_template_passes_template_validation(self) -> None:
        from rulers_lib.validation import validate_template

        errors = [
            issue
            for issue in validate_template(SKILL_ROOT)
            if issue.severity == "error"
        ]

        self.assertEqual([], errors)

    def test_registry_missing_template_is_reported(self) -> None:
        from rulers_lib.validation import validate_template

        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir) / "ai-rulers-init"
            shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (copied / "templates" / "runtime" / "domains" / "delivery" / "ROLLBACK.md").unlink()

            codes = {issue.code for issue in validate_template(copied)}

        self.assertIn("VR104", codes)

    def test_runtime_rule_missing_metadata_is_reported(self) -> None:
        from rulers_lib.validation import validate_template

        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir) / "ai-rulers-init"
            shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            rule = copied / "templates" / "runtime" / "domains" / "security" / "SECRETS.md"
            rule.write_text("# Secrets\n\nNo metadata.\n", encoding="utf-8")

            codes = {issue.code for issue in validate_template(copied)}

        self.assertIn("VR106", codes)

    def test_broken_runtime_must_load_reference_is_reported(self) -> None:
        from rulers_lib.validation import validate_template

        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir) / "ai-rulers-init"
            shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            rule = copied / "templates" / "runtime" / "domains" / "security" / "SECRETS.md"
            text = rule.read_text(encoding="utf-8").replace(
                "{{RULERS_DIR}}/security/INDEX.md",
                "{{RULERS_DIR}}/security/MISSING.md",
            )
            rule.write_text(text, encoding="utf-8")

            codes = {issue.code for issue in validate_template(copied)}

        self.assertIn("VR107", codes)


if __name__ == "__main__":
    unittest.main()
