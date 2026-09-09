"""Automatic initialization at the public CLI boundary."""

import json
import unittest
from tests import test_module_workflows as module_fixtures


class AutoInitializationTest(unittest.TestCase):
    def setUp(self):
        self.fixture = module_fixtures.ModuleWorkflowTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.workspace

    def test_default_discovery_includes_all_direct_modules_and_defers_uninitialized(
        self,
    ):
        server = self.fixture.add_submodule("server")
        self.fixture.add_submodule("ui")
        (server / "frontend").mkdir()
        (server / "backend").mkdir()
        self.fixture.git(self.root, "submodule", "deinit", "-f", "--", "ui")
        before = (self.root / "documents/rulers/RULERS_STATE.json").read_bytes()
        result = json.loads(
            self.fixture.cli(
                self.root, "init-plan", "--project-root", str(self.root)
            ).stdout
        )
        plan = json.loads((self.root / result["plan_path"]).read_text())
        self.assertEqual("workspace", plan["mode"])
        self.assertEqual(["server", "ui"], list(plan["modules"]))
        self.assertEqual("prepare-source", plan["modules"]["server"]["action"])
        self.assertEqual("unavailable", plan["modules"]["ui"]["action"])
        self.assertEqual(
            before, (self.root / "documents/rulers/RULERS_STATE.json").read_bytes()
        )
        self.assertFalse((server / "documents/rulers").exists())

    def test_init_registers_and_syncs_existing_sources_with_one_review_then_noops(self):
        for name in ("server", "ui"):
            child = self.fixture.add_submodule(name)
            self.fixture.initialize(child)
            self.fixture.seed_rules(child, name.upper() + "_POLICY")
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.assertEqual("review", result["status"])
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "approved aggregate diff",
        )
        content = self.fixture.validate_module(
            self.root,
            "--mode",
            "load",
            "--module",
            "server",
            "--rule",
            "backend/ARCHITECTURE.md",
        ).stdout
        self.assertIn("SERVER_POLICY", content)
        self.assertNotIn("UI_POLICY", content)
        again = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.assertEqual("noop", again["status"])
        applied = json.loads(
            self.fixture.cli(
                self.root, "init-apply", "--plan", again["plan_path"]
            ).stdout
        )
        self.assertEqual([], applied["changed_files"])

    def test_fresh_workspace_and_source_candidates_apply_after_one_review(self):
        import shutil

        child = self.fixture.add_submodule("server")
        prototype = self.fixture.root / "server-source"
        self.fixture.initialize(prototype)
        self.fixture.seed_rules(prototype, "NEW_SOURCE_POLICY")
        drafts = self.root / ".rulers-work/candidates"
        shutil.copytree(prototype / "documents/rulers/backend", drafts / "backend")
        shutil.copyfile(
            prototype / "documents/rulers/PROJECT_PROFILE.md", drafts / "profile.md"
        )
        shutil.copyfile(
            prototype / "documents/rulers/MODULE_EXPORT.json", drafts / "export.json"
        )
        spec = {
            "projects": {
                "workspace": {"profile": ".rulers-work/candidates/profile.md"},
                "server": {
                    "profile": ".rulers-work/candidates/profile.md",
                    "domains": {"backend": ".rulers-work/candidates/backend"},
                    "export_manifest": ".rulers-work/candidates/export.json",
                },
            }
        }
        path = self.root / ".rulers-work/candidates.json"
        path.write_text(json.dumps(spec))
        shutil.rmtree(self.root / "documents/rulers")
        (self.root / "AGENTS.md").write_text("# Human workspace instructions\n")
        planned = json.loads(
            self.fixture.cli(
                self.root, "init-plan", "--candidates", ".rulers-work/candidates.json"
            ).stdout
        )
        self.assertEqual("review", planned["status"])
        self.assertEqual([], planned["preparation"])
        self.assertFalse((child / "documents/rulers").exists())
        self.assertFalse((self.root / "documents/rulers").exists())
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            planned["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "approved all scopes",
        )
        self.assertIn(
            "Human workspace instructions", (self.root / "AGENTS.md").read_text()
        )
        import hashlib

        packet = json.loads(
            (
                self.root / "documents/rulers/modules/server/effective/source.json"
            ).read_text()
        )
        self.assertEqual(
            "sha256:"
            + hashlib.sha256(
                (child / "documents/rulers/RULERS_STATE.json").read_bytes()
            ).hexdigest(),
            packet["source"]["input_hashes"]["documents/rulers/RULERS_STATE.json"],
        )
        self.assertIn(
            "NEW_SOURCE_POLICY",
            self.fixture.validate_module(
                child,
                "--mode",
                "load",
                "--domain",
                "backend",
                "--rule",
                "backend/ARCHITECTURE.md",
            ).stdout,
        )
        self.assertIn(
            "NEW_SOURCE_POLICY",
            self.fixture.validate_module(
                self.root,
                "--mode",
                "load",
                "--module",
                "server",
                "--rule",
                "backend/ARCHITECTURE.md",
            ).stdout,
        )

    def test_overlapping_rules_wait_for_ownership_review(self):
        child = self.fixture.add_submodule("server")
        self.fixture.initialize(child)
        self.fixture.seed_rules(child, "MODULE_POLICY")
        self.fixture.seed_rules(self.root, "WORKSPACE_POLICY")
        planned = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.assertTrue(
            any(
                p["scope"] == "server" and "ownership" in p["reason"]
                for p in planned["preparation"]
            )
        )
        self.assertIn(
            "WORKSPACE_POLICY",
            self.fixture.validate_module(
                self.root,
                "--mode",
                "load",
                "--domain",
                "backend",
                "--rule",
                "backend/ARCHITECTURE.md",
            ).stdout,
        )
        spec = self.root / ".rulers-work/resolutions.json"
        spec.write_text(
            json.dumps(
                {
                    "projects": {},
                    "resolutions": [
                        {
                            "module": "server",
                            "workspace_rule": "backend/ARCHITECTURE.md",
                            "module_rule": "backend/ARCHITECTURE.md",
                            "decision": "keep-scoped",
                            "reason": "Shared contract and module implementation have separate scopes",
                        }
                    ],
                }
            )
        )
        resolved = json.loads(
            self.fixture.cli(
                self.root, "init-plan", "--candidates", ".rulers-work/resolutions.json"
            ).stdout
        )
        self.assertEqual([], resolved["preparation"])
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            resolved["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "reviewed ownership",
        )
        self.assertIn(
            "MODULE_POLICY",
            self.fixture.validate_module(
                self.root,
                "--mode",
                "load",
                "--module",
                "server",
                "--rule",
                "backend/ARCHITECTURE.md",
            ).stdout,
        )
        again = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.assertEqual("noop", again["status"])

    def test_exclusion_persists_and_new_modules_are_detected_on_repeat(self):
        for name in ("server", "ui"):
            child = self.fixture.add_submodule(name)
            self.fixture.initialize(child)
            self.fixture.seed_rules(child, name)
        first = json.loads(
            self.fixture.cli(self.root, "init-plan", "--exclude-module", "ui").stdout
        )
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            first["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "exclude ui",
        )
        plan = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        data = json.loads((self.root / plan["plan_path"]).read_text())
        self.assertEqual("excluded", data["modules"]["ui"]["action"])
        self.assertEqual("noop", plan["status"])
        self.fixture.add_submodule("worker")
        changed = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        data = json.loads((self.root / changed["plan_path"]).read_text())
        self.assertIn("worker", data["modules"])
        self.assertEqual("prepare-source", data["modules"]["worker"]["action"])

    def test_source_change_rejects_old_initialization_plan(self):
        child = self.fixture.add_submodule("server")
        self.fixture.initialize(child)
        self.fixture.seed_rules(child)
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        before = (self.root / "documents/rulers/RULERS_STATE.json").read_bytes()
        rule = child / "documents/rulers/backend/ARCHITECTURE.md"
        rule.write_text(rule.read_text() + "\nChanged after review\n")
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "stale approval",
            success=False,
        )
        self.assertEqual(
            before, (self.root / "documents/rulers/RULERS_STATE.json").read_bytes()
        )

    def test_interrupted_source_write_resumes_the_same_reviewed_batch(self):
        import sys
        from tests.test_module_workflows import CLI

        child = self.fixture.add_submodule("server")
        self.fixture.initialize(child)
        self.fixture.seed_rules(child, "RESUMED_POLICY")
        import shutil

        candidate = self.root / ".rulers-work/resume-backend"
        shutil.copytree(child / "documents/rulers/backend", candidate)
        leaf = candidate / "ARCHITECTURE.md"
        leaf.write_text(leaf.read_text() + "\nUpdated source policy\n")
        spec = self.root / ".rulers-work/resume-candidates.json"
        spec.write_text(
            json.dumps(
                {
                    "projects": {
                        "server": {
                            "domains": {"backend": ".rulers-work/resume-backend"}
                        }
                    }
                }
            )
        )
        result = json.loads(
            self.fixture.cli(
                self.root,
                "init-plan",
                "--candidates",
                ".rulers-work/resume-candidates.json",
            ).stdout
        )
        crash = """
import os,runpy,sys
sys.path.insert(0,sys.argv[1])
from rulers_lib.transactions import FileTransaction
original=FileTransaction.commit
source=sys.argv[3]
def interrupted(self):
    if str(self._layout.project_root)==source:os._exit(79)
    return original(self)
FileTransaction.commit=interrupted
cli=sys.argv[2]
sys.argv=[cli,*sys.argv[4:]]
runpy.run_path(cli,run_name='__main__')
"""
        killed = self.fixture.command(
            [
                sys.executable,
                "-c",
                crash,
                str(CLI.parent),
                str(CLI),
                str(child),
                "init-apply",
                "--plan",
                result["plan_path"],
                "--reviewed-by",
                "owner",
                "--evidence",
                "approved recoverable batch",
            ],
            success=False,
        )
        self.assertEqual(79, killed.returncode)
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "approved recoverable batch",
        )
        self.assertFalse(any(child.rglob("maintenance.lock")))
        loaded = self.fixture.validate_module(
            self.root,
            "--mode",
            "load",
            "--module",
            "server",
            "--rule",
            "backend/ARCHITECTURE.md",
        ).stdout
        self.assertIn("RESUMED_POLICY", loaded)

    def test_unresolved_workspace_candidate_never_replaces_effective_rules(self):
        import shutil

        child = self.fixture.add_submodule("server")
        self.fixture.initialize(child)
        self.fixture.seed_rules(child, "MODULE_POLICY")
        self.fixture.seed_rules(self.root, "OLD_WORKSPACE_POLICY")
        candidate = self.root / ".rulers-work/conflicting-backend"
        shutil.copytree(self.root / "documents/rulers/backend", candidate)
        leaf = candidate / "ARCHITECTURE.md"
        leaf.write_text(
            leaf.read_text().replace("OLD_WORKSPACE_POLICY", "NEW_CONFLICTING_POLICY")
        )
        spec = self.root / ".rulers-work/conflicting.json"
        spec.write_text(
            json.dumps(
                {
                    "projects": {
                        "workspace": {
                            "domains": {"backend": ".rulers-work/conflicting-backend"}
                        }
                    }
                }
            )
        )
        result = json.loads(
            self.fixture.cli(
                self.root, "init-plan", "--candidates", ".rulers-work/conflicting.json"
            ).stdout
        )
        self.assertEqual("preparation", result["status"])
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "incomplete",
            success=False,
        )
        loaded = self.fixture.validate_module(
            self.root,
            "--mode",
            "load",
            "--domain",
            "backend",
            "--rule",
            "backend/ARCHITECTURE.md",
        ).stdout
        self.assertIn("OLD_WORKSPACE_POLICY", loaded)
        self.assertNotIn("NEW_CONFLICTING_POLICY", loaded)

    def test_resume_rechecks_sources_that_have_no_writes(self):
        import sys
        from tests.test_module_workflows import CLI

        child = self.fixture.add_submodule("server")
        self.fixture.initialize(child)
        self.fixture.seed_rules(child, "OLD_POLICY")
        first = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            first["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "initial",
        )
        manifest = child / "documents/rulers/MODULE_EXPORT.json"
        value = json.loads(manifest.read_text())
        value["commands"][0]["argv"] = ["python3", "--version"]
        manifest.write_text(json.dumps(value))
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        crash = """
import os,runpy,sys
sys.path.insert(0,sys.argv[1])
from rulers_lib import initialization
original=initialization.write_plan
def interrupted(path,*args,**kwargs):
    result=original(path,*args,**kwargs)
    if str(path).endswith('.execution.json'):os._exit(79)
    return result
initialization.write_plan=interrupted
cli=sys.argv[2];sys.argv=[cli,*sys.argv[3:]]
runpy.run_path(cli,run_name='__main__')
"""
        before = (self.root / "documents/rulers/RULERS_STATE.json").read_bytes()
        killed = self.fixture.command(
            [
                sys.executable,
                "-c",
                crash,
                str(CLI.parent),
                str(CLI),
                "init-apply",
                "--plan",
                result["plan_path"],
                "--reviewed-by",
                "owner",
                "--evidence",
                "approved manifest",
            ],
            success=False,
        )
        self.assertEqual(79, killed.returncode)
        rule = child / "documents/rulers/backend/ARCHITECTURE.md"
        rule.write_text(rule.read_text() + "\nNew unreviewed policy\n")
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "approved manifest",
            success=False,
        )
        self.assertEqual(
            before, (self.root / "documents/rulers/RULERS_STATE.json").read_bytes()
        )

    def test_existing_single_project_infers_custom_rules_directory_and_noops(self):
        project = self.fixture.root / "plain-project"
        project.mkdir()
        self.fixture.cli(
            project,
            "plan",
            "--project-root",
            str(project),
            "--rulers-dir",
            "rules/agents",
            "--policy",
            "project-native",
            "--output",
            "start.json",
        )
        self.fixture.cli(project, "apply", "--plan", "start.json")
        self.fixture.cli(
            project,
            "review-profile",
            "--rulers-dir",
            "rules/agents",
            "--reviewed-by",
            "owner",
            "--evidence",
            "synthetic test",
        )
        self.fixture.cli(project, "mark-runtime-ready", "--rulers-dir", "rules/agents")
        (project / ".gitignore").write_text("/.rulers-work/\n")
        result = json.loads(self.fixture.cli(project, "init-plan").stdout)
        plan = json.loads((project / result["plan_path"]).read_text())
        self.assertEqual("rules/agents", plan["rulers_dir"])
        self.assertEqual("single-project", result["mode"])
        self.assertEqual("noop", result["status"])
        self.assertFalse((project / ".git").exists())

    def test_excluded_module_rule_symlink_does_not_block_participants(self):
        server = self.fixture.add_submodule("server")
        self.fixture.initialize(server)
        self.fixture.seed_rules(server)
        ui = self.fixture.add_submodule("ui")
        (ui / "documents").mkdir()
        (ui / "documents/rulers").symlink_to(
            self.root / "documents/rulers", target_is_directory=True
        )
        result = json.loads(
            self.fixture.cli(self.root, "init-plan", "--exclude-module", "ui").stdout
        )
        self.assertEqual("review", result["status"])
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "exclude ui",
        )
        self.assertTrue((ui / "documents/rulers").is_symlink())

    def test_removed_historical_exclusion_does_not_block_new_module(self):
        for name in ("server", "ui"):
            child = self.fixture.add_submodule(name)
            self.fixture.initialize(child)
            self.fixture.seed_rules(child)
        first = json.loads(
            self.fixture.cli(self.root, "init-plan", "--exclude-module", "ui").stdout
        )
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            first["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "exclude ui",
        )
        self.fixture.git(self.root, "rm", "-f", "ui")
        worker = self.fixture.add_submodule("worker")
        self.fixture.initialize(worker)
        self.fixture.seed_rules(worker, "NEW_WORKER")
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "include worker",
        )
        self.assertIn(
            "NEW_WORKER",
            self.fixture.validate_module(
                self.root,
                "--mode",
                "load",
                "--module",
                "worker",
                "--rule",
                "backend/ARCHITECTURE.md",
            ).stdout,
        )

    def test_execution_content_cannot_override_the_reviewed_plan(self):
        import sys, base64, hashlib
        from tests.test_module_workflows import CLI

        server = self.fixture.add_submodule("server")
        self.fixture.initialize(server)
        self.fixture.seed_rules(server, "APPROVED_POLICY")
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        crash = """
import os,runpy,sys
sys.path.insert(0,sys.argv[1])
from rulers_lib import initialization
original=initialization.write_plan
def interrupted(path,*args,**kwargs):
    value=original(path,*args,**kwargs)
    if str(path).endswith('.execution.json'):os._exit(79)
    return value
initialization.write_plan=interrupted
cli=sys.argv[2];sys.argv=[cli,*sys.argv[3:]]
runpy.run_path(cli,run_name='__main__')
"""
        killed = self.fixture.command(
            [
                sys.executable,
                "-c",
                crash,
                str(CLI.parent),
                str(CLI),
                "init-apply",
                "--plan",
                result["plan_path"],
                "--reviewed-by",
                "owner",
                "--evidence",
                "approved",
            ],
            success=False,
        )
        self.assertEqual(79, killed.returncode)
        execution_path = next((self.root / ".rulers-work").glob("*.execution.json"))
        execution = json.loads(execution_path.read_text())
        for scope in execution["changes"].values():
            for path, value in scope["files"].items():
                if path.endswith("ARCHITECTURE.md"):
                    scope["files"][path] = base64.b64encode(
                        base64.b64decode(value).replace(
                            b"APPROVED_POLICY", b"UNREVIEWED_POLICY"
                        )
                    ).decode()
        unsigned = {k: v for k, v in execution.items() if k != "digest"}
        execution["digest"] = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(
                    unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
        )
        execution_path.write_text(json.dumps(execution))
        failed = self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "owner",
            "--evidence",
            "approved",
            success=False,
        )
        self.assertIn("reviewed plan", failed.stderr)
        self.assertFalse((self.root / "documents/rulers/modules").exists())

    def test_invalid_adjustment_shape_has_actionable_error(self):
        self.fixture.add_submodule("server")
        scratch = self.root / ".rulers-work"
        scratch.mkdir(exist_ok=True)
        (scratch / "adjustments.json").write_text(json.dumps({"replace": []}))
        (scratch / "candidates.json").write_text(
            json.dumps(
                {
                    "projects": {
                        "server": {"adjustments": ".rulers-work/adjustments.json"}
                    }
                }
            )
        )
        result = self.fixture.cli(
            self.root,
            "init-plan",
            "--candidates",
            ".rulers-work/candidates.json",
            success=False,
        )
        self.assertIn("replace must be an object", result.stderr)
