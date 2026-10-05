"""Installed dependency contracts and explicit reviewed upgrade changes."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.runtime_fixture import runtime_fixture, SKILL_ROOT, REVIEW

sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from rulers_lib.domains import (DependencyContractError, effective_dependency_configs,
                               expand_reverse_dependencies, load_domain_registry)
from rulers_lib.paths import resolve_layout
from rulers_lib.state import file_sha256


class OptimizationDependenciesTest(unittest.TestCase):
    def cli(self, project, *args, success=True):
        result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts/rulers_init.py"), *args],
            cwd=project, text=True, capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode == 0, success, result.stderr + result.stdout)
        return json.loads(result.stdout) if success else result

    def state(self, project):
        return json.loads((project / "documents/rulers/RULERS_STATE.json").read_text())

    def save(self, project, state):
        (project / "documents/rulers/RULERS_STATE.json").write_text(json.dumps(state, indent=2))

    def configs(self, project, state, **kwargs):
        return effective_dependency_configs({}, state, resolve_layout(project, "documents/rulers"), **kwargs)

    def bind_rule(self, project, state, relative, text):
        path = project / relative
        path.write_text(text)
        state["managed_files"][relative]["rendered_sha256"] = file_sha256(path)

    def test_installed_declared_and_metadata_edges_survive_registry_defaults(self):
        with runtime_fixture(domains=["backend", "security", "delivery"]) as project:
            state = self.state(project)
            state["domains"]["backend"]["requires_active"] = ["security"]
            rule = "documents/rulers/delivery/CI.md"
            text = (project / rule).read_text().replace("    - \"documents/rulers/delivery/INDEX.md\"",
                "    - \"documents/rulers/delivery/INDEX.md\"\n    - documents/rulers/backend/INDEX.md")
            self.bind_rule(project, state, rule, text)
            configs = effective_dependency_configs(load_domain_registry(SKILL_ROOT), state,
                                                   resolve_layout(project, "documents/rulers"))
            self.assertEqual(["security"], configs["backend"]["requires_active"])
            self.assertEqual(["backend"], configs["delivery"]["requires_active"])
            self.assertEqual({"security", "backend", "delivery"}, set(expand_reverse_dependencies({"security"}, configs)))

    def test_navigation_is_not_an_activation_dependency(self):
        with runtime_fixture(domains=["backend", "security"]) as project:
            state = self.state(project)
            rule = "documents/rulers/backend/INDEX.md"
            self.bind_rule(project, state, rule, (project / rule).read_text() +
                           "\n[Security](documents/rulers/security/INDEX.md)\n")
            self.assertEqual([], self.configs(project, state)["backend"]["requires_active"])

    def test_bad_domain_can_be_reported_without_losing_healthy_contracts(self):
        with runtime_fixture(domains=["backend", "security"]) as project:
            state = self.state(project)
            state["domains"]["backend"]["requires_active"] = ["unknown-domain"]
            errors = []
            configs = self.configs(project, state, errors=errors)
            self.assertEqual("backend", errors[0].scope)
            self.assertEqual([], configs["security"]["requires_active"])
            self.assertEqual(["unknown-domain"], state["domains"]["backend"]["requires_active"])
            with self.assertRaises(DependencyContractError):
                self.configs(project, state)

    def test_cycle_and_unadopted_metadata_are_rejected(self):
        with runtime_fixture(domains=["backend", "security"]) as project:
            state = self.state(project)
            state["domains"]["backend"]["requires_active"] = ["security"]
            state["domains"]["security"]["requires_active"] = ["backend"]
            with self.assertRaisesRegex(DependencyContractError, "cycle"):
                self.configs(project, state)
            state["domains"]["backend"]["requires_active"] = []
            state["domains"]["security"]["requires_active"] = []
            rule = "documents/rulers/backend/ARCHITECTURE.md"
            self.bind_rule(project, state, rule, (project / rule).read_text().replace(
                "    - documents/rulers/AGENTS.md", "    - ../../outside.md"))
            (project / "documents/outside.md").write_text("# Exists, but not adopted\n")
            with self.assertRaisesRegex(DependencyContractError, "outside adopted"):
                self.configs(project, state)

    def test_relative_adopted_dependency_is_valid_but_symlink_is_rejected(self):
        with runtime_fixture(domains=["backend", "security"]) as project:
            state = self.state(project)
            rule = "documents/rulers/backend/ARCHITECTURE.md"
            text = (project / rule).read_text().replace("    - documents/rulers/AGENTS.md", "    - ../security/INDEX.md")
            self.bind_rule(project, state, rule, text)
            self.assertEqual(["security"], self.configs(project, state)["backend"]["requires_active"])
            (project / "documents/rulers/backend/alias.md").symlink_to("../security/INDEX.md")
            self.bind_rule(project, state, rule, text.replace("../security/INDEX.md", "alias.md"))
            with self.assertRaisesRegex(DependencyContractError, "symbolic link"):
                self.configs(project, state)

    def test_old_dependency_is_preserved_without_upgrade_candidate(self):
        with runtime_fixture(domains=["security", "delivery"]) as project:
            state = self.state(project)
            state["domains"]["delivery"]["requires_active"] = ["security"]
            state["template"]["fingerprint"] = "sha256:" + "0" * 64
            self.save(project, state)
            plan = self.cli(project, "plan", "--project-root", str(project), "--operation", "upgrade")
            self.assertIn("provenance is unknown", plan["dependency_preservation"])
            self.cli(project, "apply", "--plan", plan["plan_path"], *REVIEW)
            self.assertEqual(["security"], self.state(project)["domains"]["delivery"]["requires_active"])

    def test_explicit_dependency_upgrade_is_bound_degrades_and_repeats_without_changes(self):
        with runtime_fixture(domains=["security", "delivery"]) as project:
            state = self.state(project)
            state["domains"]["delivery"]["requires_active"] = ["security"]
            self.save(project, state)
            candidate = project / "dependencies.json"
            candidate.write_text(json.dumps({"delivery": []}))
            plan = self.cli(project, "plan", "--project-root", str(project), "--operation", "upgrade",
                            "--candidate-dependencies", "dependencies.json")
            self.assertEqual({"before": ["security"], "after": []}, plan["dependency_changes"]["delivery"])
            self.assertEqual(["delivery"], plan["affected_domains"])
            self.cli(project, "apply", "--plan", plan["plan_path"], *REVIEW)
            final = self.state(project)
            self.assertEqual([], final["domains"]["delivery"]["requires_active"])
            self.assertEqual("draft", final["domains"]["delivery"]["review_status"])
            self.assertEqual(2, final["domains"]["security"]["level"])
            repeated = self.cli(project, "apply", "--plan", plan["plan_path"], *REVIEW)
            self.assertEqual([], repeated["changed_files"])
            self.assertEqual(final, self.state(project))
            candidate.write_text(json.dumps({"delivery": ["security"]}))
            self.cli(project, "apply", "--plan", plan["plan_path"], *REVIEW, success=False)

    def test_candidate_requires_upgrade_and_changes_before_apply_are_rejected(self):
        with runtime_fixture(domains=["backend", "security"]) as project:
            candidate = project / "dependencies.json"
            candidate.write_text(json.dumps({"backend": ["security"]}))
            self.cli(project, "plan", "--project-root", str(project), "--candidate-dependencies", "dependencies.json", success=False)
            plan = self.cli(project, "plan", "--project-root", str(project), "--operation", "upgrade",
                            "--candidate-dependencies", "dependencies.json")
            self.assertEqual(["backend"], plan["affected_domains"])
            before = self.state(project)
            candidate.write_text(json.dumps({"backend": []}))
            self.cli(project, "apply", "--plan", plan["plan_path"], *REVIEW, success=False)
            self.assertEqual(before, self.state(project))

    def test_reconcile_uses_installed_reverse_dependency(self):
        with runtime_fixture(domains=["backend", "security"]) as project:
            state = self.state(project)
            state["domains"]["backend"]["requires_active"] = ["security"]
            self.save(project, state)
            (project / "security").mkdir()
            (project / "security/change.txt").write_text("synthetic changed evidence\n")
            plan = self.cli(project, "plan", "--project-root", str(project), "--operation", "reconcile",
                            "--changed-path", "security/change.txt")
            self.assertEqual(["backend", "security"], plan["affected_domains"])


if __name__ == "__main__":
    unittest.main()
