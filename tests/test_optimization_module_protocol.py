"""Conditional module instructions through the installed validator and snapshots."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

from scripts.runtime_fixture import runtime_fixture
import tests.test_module_workflows as module_workflows


class OptimizationModuleProtocolTest(unittest.TestCase):
    def installed_context(self, project, *selectors, cwd=None):
        validator = project / "documents/rulers/scripts/validate_rulers.py"
        result = subprocess.run(
            [sys.executable, str(validator), "--mode", "context", "--project-root", str(project), *selectors],
            cwd=cwd or project,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 2001)
        return json.loads(result.stdout)

    def test_single_project_has_no_module_protocol(self):
        with runtime_fixture() as project:
            context = self.installed_context(project)
            self.assertFalse(context["blocked"])
            self.assertNotIn("module_protocol", context)

    def test_registered_module_exposes_protocol_before_snapshot_selection(self):
        fixture = self.module_fixture()
        fixture.add_submodule("server")
        fixture.register("server")

        context = self.installed_context(fixture.workspace)

        self.assertFalse(context["blocked"])
        self.assertEqual(["server"], context["available_modules"])
        self.assertEqual({}, context["module_load"])
        protocol = context["module_protocol"]
        for required in ("绝对会话根", "主工程", "子仓库", "--project-root ROOT", "--module NAME",
                         "--domain/--rule", "--workspace-domain/--workspace-rule", "已采纳快照",
                         "用户手动", "双入口歧义"):
            self.assertIn(required, protocol)
        self.assertNotIn("references/", protocol)

    def test_selected_module_keeps_protocol_from_child_directory_and_accepted_snapshot(self):
        fixture = self.module_fixture()
        server = fixture.add_submodule("server")
        fixture.initialize(server)
        fixture.seed_rules(server, "ACCEPTED_POLICY")
        fixture.register("server")
        fixture.cli(fixture.workspace, "module-plan", "--operation", "sync", "--module", "server",
                    "--output", "sync.json")
        fixture.cli(fixture.workspace, "module-apply", "--plan", "sync.json", *module_workflows.REVIEW)
        source_rule = server / "documents/rulers/backend/ARCHITECTURE.md"
        source_rule.write_text(source_rule.read_text().replace("ACCEPTED_POLICY", "UNACCEPTED_POLICY"))

        context = self.installed_context(fixture.workspace, "--module", "server", "--domain", "backend", cwd=server)

        self.assertFalse(context["blocked"])
        self.assertFalse(context["truncated"])
        self.assertIn("module_protocol", context)
        self.assertEqual("server", context["module_load"]["server"]["code_root"])
        self.assertEqual(["documents/rulers/modules/server/effective/rules/backend/INDEX.md"],
                         context["module_load"]["server"]["indexes"])
        installed_validator = fixture.workspace / "documents/rulers/scripts/validate_rulers.py"
        loaded = fixture.command([sys.executable, str(installed_validator), "--mode", "load",
                                  "--project-root", str(fixture.workspace), "--module", "server",
                                  "--domain", "backend", "--rule", "backend/ARCHITECTURE.md"], cwd=server)
        self.assertIn("ACCEPTED_POLICY", loaded.stdout)
        self.assertNotIn("UNACCEPTED_POLICY", loaded.stdout)

    def module_fixture(self):
        fixture = module_workflows.ModuleWorkflowTest("test_register_direct_submodules_and_repeat_without_writes")
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        return fixture


if __name__ == "__main__":
    unittest.main()
