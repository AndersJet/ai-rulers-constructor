"""Git ignore configuration through reviewed initialization and collaborator clones."""

import json
import sys
import unittest
from tests import test_module_workflows as fixtures


class InitializationGitignoreTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ModuleWorkflowTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.workspace

    def initialize(self):
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "test-owner",
            "--evidence",
            "reviewed ignore change",
        )
        return result

    def test_ignore_is_reviewed_preserves_content_and_is_idempotent(self):
        path = self.root / ".gitignore"
        original = b"# Team rules\r\nnode_modules/\r\n!keep.txt"
        path.write_bytes(original)
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.assertEqual(original, path.read_bytes())
        self.assertIn("/.rulers-work/", (self.root / result["review_path"]).read_text())
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "test-owner",
            "--evidence",
            "reviewed ignore change",
        )
        self.assertEqual(original + b"\r\n/.rulers-work/\r\n", path.read_bytes())
        self.assertEqual(
            ".rulers-work/local.json",
            self.fixture.git(self.root, "check-ignore", ".rulers-work/local.json"),
        )
        again = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.assertEqual("noop", again["status"])
        self.assertEqual(1, path.read_bytes().count(b"/.rulers-work/"))

    def test_later_unignore_is_overridden_once_without_rewriting_original_lines(self):
        path = self.root / ".gitignore"
        original = b"/.rulers-work/\n!/.rulers-work/\n!/.rulers-work/keep.txt\n"
        path.write_bytes(original)
        self.initialize()
        self.assertEqual(original + b"/.rulers-work/\n", path.read_bytes())
        self.assertEqual(
            ".rulers-work/keep.txt",
            self.fixture.git(self.root, "check-ignore", ".rulers-work/keep.txt"),
        )
        self.initialize()
        self.assertEqual(original + b"/.rulers-work/\n", path.read_bytes())

    def test_clone_loads_formal_rules_without_scratch_directory(self):
        self.assertFalse((self.root / ".gitignore").exists())
        self.initialize()
        self.fixture.git(
            self.root,
            "add",
            ".gitignore",
            "AGENTS.md",
            "documents/rulers/AGENTS.md",
            "documents/rulers/INDEX.md",
            "documents/rulers/PROJECT_PROFILE.md",
            "documents/rulers/RULERS_STATE.json",
            "documents/rulers/core",
            "documents/rulers/scripts",
        )
        self.fixture.git(self.root, "commit", "-qm", "保存规范与忽略配置")
        clone = self.fixture.root / "collaborator"
        self.fixture.git(
            self.root,
            "-c",
            "protocol.file.allow=always",
            "clone",
            "-q",
            str(self.root),
            str(clone),
        )
        self.assertFalse((clone / ".rulers-work").exists())
        self.assertEqual(b"/.rulers-work/\n", (clone / ".gitignore").read_bytes())
        loaded = self.fixture.command(
            [
                sys.executable,
                str(clone / "documents/rulers/scripts/validate_rulers.py"),
                "--mode",
                "context",
                "--project-root",
                str(clone),
            ],
            cwd=clone,
        )
        self.assertFalse(json.loads(loaded.stdout)["blocked"])

    def test_already_tracked_scratch_files_remain_tracked(self):
        scratch = self.root / ".rulers-work"
        scratch.mkdir(exist_ok=True)
        tracked = scratch / "tracked.txt"
        tracked.write_text("existing tracked work\n")
        self.fixture.git(self.root, "add", ".rulers-work/tracked.txt")
        before = self.fixture.git(self.root, "ls-files", "--stage")
        self.initialize()
        self.assertEqual(before, self.fixture.git(self.root, "ls-files", "--stage"))
        self.assertEqual("existing tracked work\n", tracked.read_text())

    def test_gitignore_symlink_is_rejected_without_changing_its_target(self):
        target = self.fixture.root / "outside-ignore"
        target.write_text("keep-me\n")
        (self.root / ".gitignore").symlink_to(target)
        failed = self.fixture.cli(self.root, "init-plan", success=False)
        self.assertIn(".gitignore must be a regular project file", failed.stderr)
        self.assertEqual("keep-me\n", target.read_text())

    def test_unrelated_literal_negation_does_not_duplicate_existing_rule(self):
        path = self.root / ".gitignore"
        original = b"/.rulers-work/\n!keep.txt\n"
        path.write_bytes(original)
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        self.assertEqual("noop", result["status"])
        self.assertEqual(original, path.read_bytes())

    def test_edit_after_review_is_preserved_and_requires_replan(self):
        path = self.root / ".gitignore"
        path.write_bytes(b"node_modules/\n")
        result = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        edited = b"node_modules/\nprivate-output/\n"
        path.write_bytes(edited)
        failed = self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            result["plan_path"],
            "--reviewed-by",
            "test-owner",
            "--evidence",
            "reviewed ignore change",
            success=False,
        )
        self.assertIn("inputs changed", failed.stderr)
        self.assertEqual(edited, path.read_bytes())

    def test_interrupted_ignore_write_recovers_through_the_same_transaction(self):
        plan = json.loads(self.fixture.cli(self.root, "init-plan").stdout)
        runner = """
import os,runpy,sys
sys.path.insert(0,sys.argv[1])
from rulers_lib.transactions import FileTransaction
original=FileTransaction.commit
root=sys.argv[3]
def interrupted(self):
    if str(self._layout.project_root)==root:os._exit(79)
    return original(self)
FileTransaction.commit=interrupted
cli=sys.argv[2];sys.argv=[cli,*sys.argv[4:]]
runpy.run_path(cli,run_name='__main__')
"""
        killed = self.fixture.command(
            [
                sys.executable,
                "-c",
                runner,
                str(fixtures.CLI.parent),
                str(fixtures.CLI),
                str(self.root),
                "init-apply",
                "--plan",
                plan["plan_path"],
                "--reviewed-by",
                "test-owner",
                "--evidence",
                "reviewed ignore change",
            ],
            success=False,
        )
        self.assertEqual(79, killed.returncode)
        self.fixture.cli(
            self.root,
            "init-apply",
            "--plan",
            plan["plan_path"],
            "--reviewed-by",
            "test-owner",
            "--evidence",
            "reviewed ignore change",
        )
        self.assertEqual(b"/.rulers-work/\n", (self.root / ".gitignore").read_bytes())
        self.assertFalse(
            any((self.root / "documents/rulers").rglob("maintenance.lock"))
        )
