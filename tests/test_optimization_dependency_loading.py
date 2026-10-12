"""Task loading and readiness consume the same adopted metadata dependencies."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.runtime_fixture import runtime_fixture, SKILL_ROOT

sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from rulers_lib.paths import resolve_layout
from rulers_lib.readiness import compile_readiness
from rulers_lib.state import file_sha256


class OptimizationDependencyLoadingTest(unittest.TestCase):
    def fixture(self):
        project = self.enterContext(runtime_fixture(domains=("backend", "security", "delivery")))
        layout = resolve_layout(project, "documents/rulers")
        state = json.loads((layout.rulers_root / "RULERS_STATE.json").read_text())
        path = layout.rulers_root / "delivery/CI.md"
        before = path.read_text()
        after = before.replace('    - "documents/rulers/delivery/INDEX.md"',
                               '    - "documents/rulers/delivery/INDEX.md"\n    - documents/rulers/backend/INDEX.md')
        self.assertNotEqual(before, after)
        path.write_text(after)
        state["managed_files"]["documents/rulers/delivery/CI.md"]["rendered_sha256"] = file_sha256(path)
        self.save(layout, state)
        return layout, state

    def save(self, layout, state):
        # Synthetic reviewed State setup; never a real project approval.
        (layout.rulers_root / "RULERS_STATE.json").write_text(json.dumps(state, indent=2))

    def validator(self, layout, mode, *args, success=True):
        result = subprocess.run([sys.executable, str(layout.rulers_root / "scripts/validate_rulers.py"),
            "--mode", mode, "--project-root", str(layout.project_root),
            "--rulers-dir", layout.rulers_dir, "--format", "json", *args],
            cwd=layout.project_root, text=True, capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode == 0, success, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def assess(self, layout, state):
        source = {role: ["documents/rulers/delivery/CI.md"] for role in ("security", "quality", "rollback")}
        declaration = compile_readiness(layout, state, "delivery", source)
        state["domains"]["delivery"]["review"]["readiness"] = declaration
        self.save(layout, state)
        return declaration

    def test_healthy_metadata_dependency_is_automatically_loaded(self):
        layout, _ = self.fixture()
        context = self.validator(layout, "context", "--domain", "delivery")
        self.assertFalse(context["blocked"])
        bundle = self.validator(layout, "load", "--domain", "delivery", "--rule", "delivery/CI.md")
        self.assertIn("documents/rulers/backend/INDEX.md", bundle["files"])
        self.assertIn("documents/rulers/delivery/CI.md", bundle["files"])
        self.assertNotIn("documents/rulers/security/INDEX.md", bundle["files"])

    def test_draft_metadata_dependency_blocks_source_but_not_independent_domain(self):
        layout, state = self.fixture()
        state["domains"]["backend"].update(level=0, review_status="draft", level3_ready=False)
        self.save(layout, state)
        context = self.validator(layout, "context", "--domain", "delivery")
        self.assertTrue(context["blocked"])
        self.assertNotIn("delivery", context["available_domains"])
        healthy = self.validator(layout, "context", "--domain", "security")
        self.assertFalse(healthy["blocked"])
        self.validator(layout, "load", "--domain", "security", "--rule", "security/SECRETS.md")

    def test_readiness_binds_metadata_owner_and_is_revoked_when_it_becomes_draft(self):
        layout, state = self.fixture()
        declaration = self.assess(layout, state)
        self.assertIn("backend", declaration["bindings"])
        self.assertEqual(["backend"], declaration["bindings"]["delivery"]["requires_active"])
        context = self.validator(layout, "context", "--domain", "delivery")
        self.assertTrue(context["readiness"]["delivery"]["ready"])
        state["domains"]["backend"].update(level=0, review_status="draft", level3_ready=False)
        self.save(layout, state)
        context = self.validator(layout, "context", "--domain", "delivery")
        self.assertFalse(context.get("readiness", {}).get("delivery", {}).get("ready", False))
        self.assertNotIn("delivery", context["level3_ready"])

    def test_invalid_existing_readiness_is_warning_and_unassessed_is_quiet(self):
        layout, state = self.fixture()
        unassessed = self.validator(layout, "runtime")
        self.assertFalse(unassessed["issues"])
        self.assess(layout, state)
        state["domains"]["delivery"]["review"]["readiness"]["digest"] = "sha256:" + "0" * 64
        self.save(layout, state)
        runtime = self.validator(layout, "runtime")
        self.assertTrue(runtime["issues"])
        self.assertTrue(all(issue["severity"] == "warning" for issue in runtime["issues"]))
        context = self.validator(layout, "context", "--domain", "delivery")
        self.assertFalse(context["blocked"])
        self.assertFalse(context["readiness"]["delivery"]["ready"])


if __name__ == "__main__":
    unittest.main()
