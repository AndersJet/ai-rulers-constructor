"""Public loading contract: cwd independence, conditional core and exact budgets."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

from scripts.runtime_fixture import runtime_fixture
from scripts.report_context_budget import measure_context_budget, summarize_reads


class TaskLoadingTest(unittest.TestCase):
    def run_cli(self, project, *args, rulers_dir="documents/rulers", cwd=None):
        return subprocess.run(
            [sys.executable, str(project / rulers_dir / "scripts/validate_rulers.py"),
             "--project-root", str(project), "--rulers-dir", rulers_dir, *args],
            cwd=cwd or project, capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_entry_and_diagnostic_commands_work_below_root_with_spaces(self):
        rulers_dir = "docs/custom rules"
        with runtime_fixture(rulers_dir=rulers_dir, domains=("backend",)) as project:
            child = project / "nested folder"
            child.mkdir()
            entry = (project / rulers_dir / "AGENTS.md").read_text()
            command = re.search(r'`(python3 "\$ROOT/[^`]+)`', entry).group(1)
            result = subprocess.run(
                ["/bin/sh", "-c", command + " --mode load --domain backend --rule backend/TESTING.md"],
                cwd=child, capture_output=True, text=True,
                env={**os.environ, "ROOT": str(project), "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("backend/TESTING.md", result.stdout)
            hard = project / rulers_dir / "core/HARD_CONSTRAINTS.md"
            hard.write_text(hard.read_text() + "\nDrift\n")
            context = json.loads(self.run_cli(project, "--mode", "context", rulers_dir=rulers_dir).stdout)
            self.assertTrue(context["blocked"])
            diagnostic = subprocess.run(shlex.split(context["details_command"]), cwd=child,
                                        capture_output=True, text=True)
            self.assertEqual(diagnostic.returncode, 1, diagnostic.stderr)
            self.assertTrue(any(i["code"] == "VR040" for i in json.loads(diagnostic.stdout)["issues"]))

    def test_conditional_core_and_policy_dependencies_are_explicit_only(self):
        with runtime_fixture() as project:
            basic = self.run_cli(project, "--mode", "load", "--format", "json")
            self.assertEqual(basic.returncode, 0, basic.stderr)
            files = json.loads(basic.stdout)["files"]
            self.assertNotIn("documents/rulers/core/GIT_COMMIT_CONVENTION.md", files)
            self.assertNotIn("documents/rulers/core/RULER_MAINTENANCE.md", files)
            for rule in ("RULER_MAINTENANCE", "DOC_GOVERNANCE", "GIT_COMMIT_CONVENTION", "CHANGELOG_MAINTENANCE"):
                with self.subTest(rule=rule):
                    result = self.run_cli(project, "--mode", "load", "--rule", f"core/{rule}.md", "--format", "json")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    selected = json.loads(result.stdout)["files"]
                    self.assertIn(f"documents/rulers/core/{rule}.md", selected)
                    self.assertEqual(len(selected), len(set(selected)))
                    if rule in {"GIT_COMMIT_CONVENTION", "CHANGELOG_MAINTENANCE"}:
                        self.assertIn("documents/rulers/core/GIT_COMMIT_CONVENTION.md", selected)
                        self.assertIn("documents/rulers/core/CHANGELOG_MAINTENANCE.md", selected)

    def test_native_policy_cannot_load_strict_rules_even_if_file_is_present(self):
        with runtime_fixture(policy="project-native") as project:
            path = project / "documents/rulers/core/GIT_COMMIT_CONVENTION.md"
            path.write_text("# Unadopted policy\n")
            result = self.run_cli(project, "--mode", "load", "--rule", "core/GIT_COMMIT_CONVENTION.md")
            self.assertEqual(result.returncode, 2)
            maintenance = self.run_cli(project, "--mode", "load", "--rule", "core/RULER_MAINTENANCE.md")
            self.assertEqual(maintenance.returncode, 0, maintenance.stderr)

    def test_conditional_core_drift_and_outside_rules_cannot_be_loaded(self):
        with runtime_fixture() as project:
            for rule in ("../outside.md", "core/UNKNOWN.md"):
                self.assertEqual(self.run_cli(project, "--mode", "load", "--rule", rule).returncode, 2)
            path = project / "documents/rulers/core/RULER_MAINTENANCE.md"
            path.write_text(path.read_text() + "\nDrift\n")
            self.assertEqual(self.run_cli(project, "--mode", "load", "--rule", "core/RULER_MAINTENANCE.md").returncode, 2)

    def test_domain_only_is_navigation_and_explicit_leaf_bytes_are_exact(self):
        with runtime_fixture(domains=("backend",)) as project:
            result = self.run_cli(project, "--mode", "load", "--domain", "backend", "--format", "json")
            self.assertEqual(result.returncode, 0, result.stderr)
            base = json.loads(result.stdout)
            leaf = "documents/rulers/backend/TESTING.md"
            self.assertNotIn(leaf, base["files"])
            args = ("--mode", "load", "--domain", "backend", "--rule", "backend/TESTING.md")
            bundle = json.loads(self.run_cli(project, *args, "--format", "json").stdout)
            body = self.run_cli(project, *args, "--format", "text").stdout
            self.assertIn(leaf, bundle["files"])
            self.assertEqual(bundle["bytes"], len(body.removesuffix("\n").encode("utf-8")))
            report = measure_context_budget(project_root=project, domains=("backend",),
                                            rules=("backend/TESTING.md",), include_token_trend=False)
            self.assertTrue(report["all_pass"], report)
            self.assertEqual(report["measurements"]["loaded_content_bytes"], bundle["bytes"])
            self.assertIn(leaf, report["load_graph"]["files"])
            self.assertGreater(report["measurements"]["fixed_chain_bytes"], report["measurements"]["direct_load_bytes"])
            self.assertFalse(report["reads"]["observed"])

    def test_read_measurement_requires_explicit_valid_observations(self):
        reads = summarize_reads([{"path": "core", "output_bytes": 12}, {"path": "core", "output_bytes": 8}])
        self.assertEqual(reads["output_bytes"], 20)
        self.assertEqual(reads["repeated_paths"], ["core"])
        for invalid in ({}, [None], [{"path": "x", "output_bytes": True}], [{"path": "x", "output_bytes": -1}]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                summarize_reads(invalid)

    def test_replay_fixture_has_valid_minimal_rules_and_preserves_existing_target(self):
        from scripts.prepare_loading_replay import prepare
        from scripts.runtime_fixture import SKILL_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            record = prepare(SKILL_ROOT, target, "blocked-choice")
            result = self.run_cli(target, "--mode", "load", "--domain", "backend", "--rule", "backend/TESTING.md")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(record["synthetic"])
            state = json.loads((target / "documents/rulers/RULERS_STATE.json").read_text())
            self.assertEqual({"INDEX.md", "TESTING.md"}, set(state["domains"]["backend"]["required_files"]))
            before = (target / "cart.py").read_bytes()
            with self.assertRaises(ValueError):
                prepare(SKILL_ROOT, target, "fix")
            self.assertEqual(before, (target / "cart.py").read_bytes())


if __name__ == "__main__":
    unittest.main()
