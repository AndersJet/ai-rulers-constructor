"""Module workflows at the public CLI seam, backed by real local Git repositories."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.runtime_fixture import SKILL_ROOT, REVIEW

MODULE_SKILL_ROOT = Path(os.environ.get("RULERS_TEST_SKILL_ROOT", str(SKILL_ROOT)))
CLI = MODULE_SKILL_ROOT / "scripts/rulers_init.py"
VALIDATOR = MODULE_SKILL_ROOT / "scripts/validate_rulers.py"


class ModuleWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="module-workflows-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.git(self.workspace, "init", "-q")
        self.git(self.workspace, "config", "user.name", "Synthetic Test")
        self.git(self.workspace, "config", "user.email", "test@example.invalid")
        (self.workspace / "README.md").write_text("Synthetic workspace\n")
        self.git(self.workspace, "add", "README.md")
        self.git(self.workspace, "commit", "-qm", "初始化测试仓库")
        self.initialize(self.workspace)

    def command(self, argv, *, cwd=None, success=True):
        result = subprocess.run(argv, cwd=cwd or self.workspace, capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1"})
        if success:
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout)
        return result

    def git(self, root, *args):
        return self.command(["git", "-C", str(root), *args]).stdout.strip()

    def cli(self, root, *args, success=True):
        return self.command([sys.executable, str(CLI), *args], cwd=root, success=success)

    def initialize(self, project):
        result = self.cli(project, "plan", "--project-root", str(project), "--policy", "project-native")
        plan = json.loads(result.stdout)["plan_path"]
        self.cli(project, "apply", "--plan", str(project / plan))
        self.cli(project, "review-profile", "--project-root", str(project), *REVIEW)
        self.cli(project, "mark-runtime-ready", "--project-root", str(project))

    def add_submodule(self, name):
        source = self.root / (name + "-source")
        source.mkdir(parents=True)
        self.git(source, "init", "-q")
        self.git(source, "config", "user.name", "Synthetic Test")
        self.git(source, "config", "user.email", "test@example.invalid")
        (source / "README.md").write_text("Synthetic module\n")
        self.git(source, "add", ".")
        self.git(source, "commit", "-qm", "初始化模块")
        self.git(self.workspace, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(source), name)
        return self.workspace / name

    def seed_rules(self, project, marker="MODULE_RULE"):
        draft = project / "rule-draft"
        draft.mkdir()
        metadata = "```yaml\nmetadata:\n  applies_to:\n    - '**/*'\n  trigger_keywords:\n    - module\n  must_load_with: []\n```\n"
        (draft / "INDEX.md").write_text("# Backend\n" + metadata + "\n[Architecture](ARCHITECTURE.md)\n")
        (draft / "ARCHITECTURE.md").write_text("# Architecture\n" + metadata + "\n" + marker + "\n")
        self.cli(project, "rules-plan", "--domain", "backend", "--candidate-dir", "rule-draft", "--reason", "synthetic module", "--output", "rules-plan.json")
        self.cli(project, "rules-apply", "--plan", "rules-plan.json", "--reviewed-by", "test-owner", "--evidence", "test-only")
        self.cli(project, "activate-domain", "--domain", "backend", *REVIEW)
        manifest = {"version": 1, "rules": [{"path": "backend/INDEX.md", "domain": "backend"},
            {"path": "backend/ARCHITECTURE.md", "domain": "backend"}], "profile_scopes": ["core", "backend"],
            "commands": [{"name": "test", "argv": ["python3", "-m", "unittest"], "cwd": "."}],
            "evidence": ["README.md"]}
        (project / "documents/rulers/MODULE_EXPORT.json").write_text(json.dumps(manifest))
        return manifest

    def register(self, name):
        self.cli(self.workspace, "module-plan", "--operation", "register", "--module", name, "--output", f"register-{name}.json")
        self.cli(self.workspace, "module-apply", "--plan", f"register-{name}.json", *REVIEW)

    def validate_module(self, root, *args, success=True):
        return self.command([sys.executable, str(VALIDATOR), "--project-root", str(root), *args], success=success)

    def test_register_direct_submodules_and_repeat_without_writes(self):
        server = self.add_submodule("server")
        self.add_submodule("ui")
        (server / "frontend").mkdir()
        (server / "backend").mkdir()
        before = self.git(self.workspace, "diff", "--cached")
        discovery = json.loads(self.cli(self.workspace, "modules").stdout)
        self.assertEqual(["server", "ui"], [m["name"] for m in discovery["discovered"]])
        plan = json.loads(self.cli(self.workspace, "module-plan", "--operation", "register", "--module", "server", "--output", "register.json").stdout)
        self.assertEqual("register", plan["operation"])
        self.cli(self.workspace, "module-apply", "--plan", "register.json", *REVIEW)
        listing = json.loads(self.cli(self.workspace, "modules").stdout)
        self.assertEqual(["server"], list(listing["registered"]))
        self.assertEqual("registered", listing["registered"]["server"]["phase"])
        repeated = json.loads(self.cli(self.workspace, "module-apply", "--plan", "register.json", *REVIEW).stdout)
        self.assertEqual([], repeated["changed_files"])
        self.assertEqual(before, self.git(self.workspace, "diff", "--cached"))
        self.git(self.workspace,"config","-f",".gitmodules","submodule.server.url","https://example.invalid/rebound.git")
        self.cli(self.workspace,"module-apply","--plan","register.json",*REVIEW,success=False)

    def test_plan_output_rejects_redirected_absolute_path(self):
        self.add_submodule("server")
        target = self.workspace / "real-output"
        target.mkdir()
        alias = self.workspace / "output-alias"
        alias.symlink_to(target,target_is_directory=True)
        self.cli(self.workspace,"module-plan","--operation","register","--module","server",
                 "--output",str(alias / "plan.json"),success=False)
        self.assertFalse((target / "plan.json").exists())

    def test_module_name_with_path_separator_keeps_portable_references(self):
        server = self.add_submodule("apps/server")
        self.initialize(server)
        self.seed_rules(server,"NESTED_PATH_POLICY")
        self.register("apps/server")
        self.cli(self.workspace,"module-plan","--operation","sync","--module","apps/server","--output","sync.json")
        self.cli(self.workspace,"module-apply","--plan","sync.json",*REVIEW)
        loaded = self.validate_module(self.workspace,"--mode","load","--module","apps/server","--rule","backend/ARCHITECTURE.md").stdout
        self.assertIn("NESTED_PATH_POLICY",loaded)

    def test_export_captures_uncommitted_rules_without_framework_state(self):
        server = self.add_submodule("server")
        self.initialize(server)
        self.seed_rules(server, "UNCOMMITTED_MODULE_RULE")
        before = self.git(server, "rev-parse", "HEAD")
        result = self.cli(server, "module-export", "--output", "export.json")
        summary = json.loads(result.stdout)
        exported = json.loads((server / "export.json").read_text())
        self.assertTrue(exported["source"]["dirty"])
        self.assertEqual(before, exported["source"]["head"])
        self.assertIn("UNCOMMITTED_MODULE_RULE", exported["rules"]["backend/ARCHITECTURE.md"]["text"])
        self.assertNotIn("managed_files", exported)
        self.assertNotIn("core/HARD_CONSTRAINTS.md", exported["rules"])
        self.assertEqual(exported["content_id"], summary["content_id"])
        again = self.cli(server, "module-export", "--output", "export-again.json")
        self.assertEqual(summary["content_id"], json.loads(again.stdout)["content_id"])
        self.assertEqual(before, self.git(server, "rev-parse", "HEAD"))

    def test_first_sync_loads_reviewed_snapshot_without_source_writes(self):
        server = self.add_submodule("server")
        self.initialize(server)
        self.seed_rules(server, "SERVER_POLICY")
        leaf = server / "documents/rulers/backend/ARCHITECTURE.md"
        leaf.write_text(leaf.read_text().replace("must_load_with: []", "must_load_with:\n    - documents/rulers/PROJECT_PROFILE.md"))
        self.register("server")
        source_before = (server / "documents/rulers/RULERS_STATE.json").read_bytes()
        result = self.cli(self.workspace, "module-plan", "--operation", "sync", "--module", "server", "--output", "sync.json")
        self.assertTrue(json.loads(result.stdout)["requires_review"])
        differences = json.loads((self.workspace / "sync.json").read_text())["changes"]["server"]
        self.assertEqual("add", differences["rules"]["backend/ARCHITECTURE.md"]["operation"])
        self.assertIn("SERVER_POLICY", differences["rules"]["backend/ARCHITECTURE.md"]["diff"])
        self.validate_module(self.workspace, "--mode", "load", "--module", "server", success=False)
        self.cli(self.workspace, "module-apply", "--plan", "sync.json", *REVIEW)
        loaded = self.validate_module(self.workspace, "--mode", "load", "--module", "server", "--domain", "backend", "--rule", "backend/ARCHITECTURE.md").stdout
        self.assertIn("SERVER_POLICY", loaded)
        self.assertIn("server", loaded)
        self.assertEqual(source_before, (server / "documents/rulers/RULERS_STATE.json").read_bytes())
        result = self.cli(self.workspace, "module-plan", "--operation", "sync", "--module", "server", "--output", "same-sync.json")
        self.assertFalse(json.loads(result.stdout)["requires_review"])
        repeat = json.loads(self.cli(self.workspace, "module-apply", "--plan", "same-sync.json").stdout)
        self.assertEqual([], repeat["changed_files"])

    def test_adjustments_survive_sync_and_source_conflicts_require_review(self):
        server = self.add_submodule("server")
        self.initialize(server)
        manifest = self.seed_rules(server, "SOURCE_POLICY")
        rules = server / "documents/rulers/backend"
        (rules / "UNUSED.md").write_text((rules / "ARCHITECTURE.md").read_text().replace("SOURCE_POLICY","UNUSED_POLICY"))
        (rules / "INDEX.md").write_text((rules / "INDEX.md").read_text()+"\n[Unused](UNUSED.md)\n")
        manifest["rules"].append({"path":"backend/UNUSED.md","domain":"backend"})
        (server / "documents/rulers/MODULE_EXPORT.json").write_text(json.dumps(manifest))
        self.register("server")
        self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","sync.json")
        self.cli(self.workspace,"module-apply","--plan","sync.json",*REVIEW)
        (self.workspace / "override.md").write_text((rules / "ARCHITECTURE.md").read_text().replace("SOURCE_POLICY","WORKSPACE_POLICY"))
        (self.workspace / "adjust.json").write_text(json.dumps({"replace":{"backend/ARCHITECTURE.md":"override.md"},"disable":["backend/UNUSED.md"]}))
        (self.workspace / "invalid-adjust.json").write_text('{"replace":[]}')
        invalid = self.cli(self.workspace,"module-plan","--operation","adjust","--module","server","--adjustments","invalid-adjust.json","--output","invalid-plan.json",success=False)
        self.assertIn("replace must be an object", invalid.stderr)
        self.cli(self.workspace,"module-plan","--operation","adjust","--module","server","--adjustments","adjust.json","--output","adjust-plan.json")
        self.cli(self.workspace,"module-apply","--plan","adjust-plan.json",*REVIEW)
        loaded = self.validate_module(self.workspace,"--mode","load","--module","server","--rule","backend/ARCHITECTURE.md").stdout
        self.assertIn("WORKSPACE_POLICY",loaded)
        self.assertNotIn("UNUSED_POLICY",loaded)
        self.assertIn("SOURCE_POLICY",(rules / "ARCHITECTURE.md").read_text())
        (rules / "ARCHITECTURE.md").write_text((rules / "ARCHITECTURE.md").read_text()+"\nSource version two\n")
        conflict = json.loads(self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","conflict.json").stdout)
        self.assertTrue(conflict["conflicts"])
        self.cli(self.workspace,"module-apply","--plan","conflict.json",*REVIEW,success=False)
        self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--adjustments","adjust.json","--output","resolved.json")
        self.cli(self.workspace,"module-apply","--plan","resolved.json",*REVIEW)
        self.validate_module(self.workspace,"--mode","load","--module","server","--rule","backend/UNUSED.md",success=False)
        (rules / "UNUSED.md").unlink()
        (rules / "INDEX.md").write_text((rules / "INDEX.md").read_text().replace("\n[Unused](UNUSED.md)\n",""))
        manifest["rules"] = [r for r in manifest["rules"] if r["path"] != "backend/UNUSED.md"]
        (server / "documents/rulers/MODULE_EXPORT.json").write_text(json.dumps(manifest))
        deletion = json.loads(self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","delete-conflict.json").stdout)
        self.assertTrue(deletion["conflicts"])
        self.cli(self.workspace,"module-apply","--plan","delete-conflict.json",*REVIEW,success=False)

    def test_runtime_rejects_changed_git_binding_without_scanning_rule_sources(self):
        server = self.add_submodule("server")
        self.initialize(server)
        self.seed_rules(server,"BOUND_POLICY")
        self.register("server")
        self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","sync.json")
        self.cli(self.workspace,"module-apply","--plan","sync.json",*REVIEW)
        # Ordinary consumption uses the accepted snapshot, not an export update scan.
        (server / "documents/rulers/MODULE_EXPORT.json").write_text("unfinished local edit")
        self.assertIn("BOUND_POLICY",self.validate_module(self.workspace,"--mode","load","--module","server","--rule","backend/ARCHITECTURE.md").stdout)
        self.git(self.workspace,"config","-f",".gitmodules","submodule.server.url","https://example.invalid/different.git")
        self.validate_module(self.workspace,"--mode","load","--module","server",success=False)

    def test_migration_prepares_source_then_atomically_switches_workspace_rules(self):
        server = self.add_submodule("server")
        self.seed_rules(self.workspace,"LEGACY_MODULE_RULE")
        self.register("server")
        candidate = self.workspace / "migration-candidate"
        candidate.mkdir()
        import shutil
        shutil.copytree(self.workspace / "documents/rulers/backend",candidate / "backend")
        for name in ("PROJECT_PROFILE.md","MODULE_EXPORT.json"):
            shutil.copyfile(self.workspace / "documents/rulers" / name,candidate / name)
        self.cli(self.workspace,"module-migrate-plan","--module","server","--candidate-dir","migration-candidate",
                 "--retire-domain","backend","--output","migration.json")
        self.assertFalse((server / "documents/rulers").exists())
        # Kill the process after source files/State have landed, before transaction cleanup.
        crash = """
import os, runpy, sys
sys.path.insert(0, sys.argv[1])
from rulers_lib.transactions import FileTransaction
original = FileTransaction.commit
def interrupted(self):
    if self._layout.project_root.name == 'server':
        os._exit(91)
    return original(self)
FileTransaction.commit = interrupted
cli = sys.argv[2]
sys.argv = [cli, *sys.argv[3:]]
runpy.run_path(cli, run_name='__main__')
"""
        killed = self.command([sys.executable,"-c",crash,str(CLI.parent),str(CLI),"module-migrate-apply",
            "--plan","migration.json","--stage","source",*REVIEW],success=False)
        self.assertEqual(91,killed.returncode)
        self.cli(self.workspace,"module-migrate-apply","--plan","migration.json","--stage","source",*REVIEW)
        self.assertFalse(any(server.rglob("maintenance.lock")))
        self.assertTrue((server / "documents/rulers/MODULE_EXPORT.json").is_file())
        old = self.command([sys.executable,str(VALIDATOR),"--mode","load","--project-root",str(self.workspace),
                            "--domain","backend","--rule","backend/ARCHITECTURE.md"]).stdout
        self.assertIn("LEGACY_MODULE_RULE",old)
        self.cli(self.workspace,"module-migrate-apply","--plan","migration.json","--stage","complete",*REVIEW)
        loaded = self.validate_module(self.workspace,"--mode","load","--module","server","--rule","backend/ARCHITECTURE.md").stdout
        self.assertIn("LEGACY_MODULE_RULE",loaded)
        context = json.loads(self.command([sys.executable,str(VALIDATOR),"--mode","context","--project-root",str(self.workspace),"--domain","backend"]).stdout)
        self.assertNotIn("backend",context["routes"])
        again = self.cli(self.workspace,"module-migrate-apply","--plan","migration.json","--stage","complete",*REVIEW)
        self.assertEqual([],json.loads(again.stdout)["changed_files"])

    def test_stale_source_plan_is_rejected_without_workspace_writes(self):
        server = self.add_submodule("server")
        self.initialize(server)
        self.seed_rules(server)
        self.register("server")
        self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","sync.json")
        before = (self.workspace / "documents/rulers/RULERS_STATE.json").read_bytes()
        leaf = server / "documents/rulers/backend/ARCHITECTURE.md"
        leaf.write_text(leaf.read_text()+"\nNew unreviewed policy\n")
        rejected = self.cli(self.workspace,"module-apply","--plan","sync.json",*REVIEW,success=False)
        self.assertIn("inputs changed", rejected.stderr)
        self.assertEqual(before,(self.workspace / "documents/rulers/RULERS_STATE.json").read_bytes())
        self.assertFalse((self.workspace / "documents/rulers/modules").exists())

    def test_custom_core_must_be_classified_and_ignored_inputs_are_dirty(self):
        server = self.add_submodule("server")
        self.initialize(server)
        manifest = self.seed_rules(server)
        core = server / "documents/rulers/core/HARD_CONSTRAINTS.md"
        core.write_text(core.read_text()+"\nStandalone harness constraint\n")
        error = self.cli(server,"module-export","--output","export.json",success=False)
        self.assertIn("Classify customized core",error.stderr)
        manifest["core_decisions"] = {"core/HARD_CONSTRAINTS.md":{"classification":"framework-only","reason":"Standalone harness policy; owner reviewed"}}
        (server / "documents/rulers/MODULE_EXPORT.json").write_text(json.dumps(manifest))
        (server / ".gitignore").write_text("*\n")
        self.git(server,"add","-f",".gitignore")
        self.git(server,"-c","user.name=Synthetic Test","-c","user.email=test@example.invalid","commit","-qm","忽略测试规则")
        self.assertEqual("",self.git(server,"status","--porcelain"))
        self.cli(server,"module-export","--output","export.json")
        self.assertTrue(json.loads((server / "export.json").read_text())["source"]["dirty"])

    def test_workspace_constraints_and_module_selection_remain_separate(self):
        server = self.add_submodule("server")
        ui = self.add_submodule("ui")
        self.seed_rules(self.workspace,"COMPOSITION_POLICY")
        for root, marker in ((server,"SERVER_ONLY"),(ui,"UI_ONLY")):
            self.initialize(root)
            self.seed_rules(root,marker)
            self.register(root.name)
        self.cli(self.workspace,"module-plan","--operation","sync","--output","all.json")
        self.cli(self.workspace,"module-apply","--plan","all.json",*REVIEW)
        selected = self.validate_module(self.workspace,"--mode","load","--module","server","--rule","backend/ARCHITECTURE.md").stdout
        self.assertIn("SERVER_ONLY",selected)
        self.assertNotIn("UI_ONLY",selected)
        self.assertNotIn("COMPOSITION_POLICY",selected)
        combined = self.validate_module(self.workspace,"--mode","load","--module","server","--module","ui",
            "--rule","backend/ARCHITECTURE.md","--workspace-domain","backend","--workspace-rule","backend/ARCHITECTURE.md").stdout
        for marker in ("SERVER_ONLY","UI_ONLY","COMPOSITION_POLICY"):
            self.assertIn(marker,combined)
        standalone = self.validate_module(server,"--mode","load","--domain","backend","--rule","backend/ARCHITECTURE.md").stdout
        self.assertIn("SERVER_ONLY",standalone)
        self.assertNotIn("COMPOSITION_POLICY",standalone)
        from_child = self.command([sys.executable,str(VALIDATOR),"--project-root",str(self.workspace),"--mode","load",
            "--module","ui","--rule","backend/ARCHITECTURE.md"],cwd=server).stdout
        self.assertIn("UI_ONLY",from_child)

    def test_uninitialized_module_reports_unavailable_and_blocks_sync(self):
        server = self.add_submodule("server")
        self.git(self.workspace,"submodule","deinit","-f","--","server")
        self.register("server")
        listing = json.loads(self.cli(self.workspace,"modules").stdout)
        self.assertEqual("unavailable",listing["registered"]["server"]["phase"])
        error = self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","sync.json",success=False)
        self.assertIn("not initialized",error.stderr)

    def test_multi_domain_module_loads_only_selected_domain_and_rejects_snapshot_drift(self):
        server = self.add_submodule("server")
        self.initialize(server)
        manifest = self.seed_rules(server,"BACKEND_ONLY")
        rules = server / "documents/rulers"
        (rules / "database").mkdir(exist_ok=True)
        for name in ("INDEX.md","ARCHITECTURE.md"):
            (rules / "database" / name).write_text((rules / "backend" / name).read_text().replace("BACKEND_ONLY","DATABASE_ONLY"))
            manifest["rules"].append({"path":"database/"+name,"domain":"database"})
        manifest["profile_scopes"].append("database")
        (rules / "MODULE_EXPORT.json").write_text(json.dumps(manifest))
        self.register("server")
        self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","sync.json")
        self.cli(self.workspace,"module-apply","--plan","sync.json",*REVIEW)
        result = self.validate_module(self.workspace,"--mode","load","--module","server","--domain","backend","--rule","backend/ARCHITECTURE.md").stdout
        self.assertIn("BACKEND_ONLY",result)
        self.assertNotIn("DATABASE_ONLY",result)
        context = self.validate_module(self.workspace,"--mode","context","--module","server","--domain","backend").stdout
        self.assertLessEqual(len(context.encode()),2001)
        self.assertFalse(json.loads(context)["blocked"])
        imported = self.workspace / "documents/rulers/modules/server/effective/rules/backend/ARCHITECTURE.md"
        imported.write_text(imported.read_text()+"\nManual workspace edit\n")
        self.validate_module(self.workspace,"--mode","load","--module","server",success=False)
        conflict = json.loads(self.cli(self.workspace,"module-plan","--operation","sync","--module","server","--output","drift.json").stdout)
        self.assertTrue(conflict["conflicts"])
        self.cli(self.workspace,"module-apply","--plan","drift.json",*REVIEW,success=False)
        self.assertIn("Manual workspace edit",imported.read_text())
