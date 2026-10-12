"""User-facing scaffold contracts exercised through the public CLI."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.runtime_fixture import runtime_fixture, SKILL_ROOT, REVIEW

sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from rulers_lib.paths import resolve_layout
from rulers_lib.transactions import maintenance_lock


class ScaffoldLifecycleTest(unittest.TestCase):
    def run_cli(self, project, *args, success=True):
        result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts/rulers_init.py"), *args],
                                cwd=project, capture_output=True, text=True)
        if success:
            self.assertEqual(0, result.returncode, result.stderr)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout)
        return result

    def target(self, project):
        return ("--project-root", str(project), "--rulers-dir", "documents/rulers")

    def validate(self, project, mode="runtime", *extra):
        result = subprocess.run([sys.executable, str(project / "documents/rulers/scripts/validate_rulers.py"),
                                 "--mode", mode, *self.target(project), "--format", "json", *extra],
                                cwd=project, capture_output=True, text=True)
        return result

    def state(self, project):
        return json.loads((project / "documents/rulers/RULERS_STATE.json").read_text())

    def test_pure_greenfield_can_adopt_a_pruned_domain_from_approved_decisions(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td).resolve()
            (project / "ADR.md").write_text("Approved: separate domain logic from persistence.\n")
            summary = json.loads(self.run_cli(project, "plan", *self.target(project)).stdout)
            self.run_cli(project, "apply", "--plan", summary["plan_path"])
            profile = project / "documents/rulers/PROJECT_PROFILE.md"
            text = profile.read_text().replace(
                "| --- | --- | --- | --- | --- |",
                "| --- | --- | --- | --- | --- |\n| 分离领域与持久化 | approved | ADR.md | backend | high |",
            )
            profile.write_text(text)
            self.run_cli(project, "review-profile", *self.target(project), *REVIEW)
            draft = project / "draft"
            draft.mkdir()
            metadata = "```yaml\nmetadata:\n  applies_to:\n    - '**/*'\n  trigger_keywords:\n    - architecture\n  must_load_with: []\n```\n"
            (draft / "INDEX.md").write_text("# Domain\n" + metadata + "\n[Architecture](ARCHITECTURE.md)\n")
            (draft / "ARCHITECTURE.md").write_text("# Approved architecture\n" + metadata + "\nKeep persistence separate.\n")
            self.run_cli(project, "rules-plan", *self.target(project), "--domain", "backend", "--candidate-dir", "draft",
                         "--reason", "Approved greenfield ADR", "--output", "rule-plan.json")
            self.run_cli(project, "rules-apply", "--plan", "rule-plan.json", "--reviewed-by", "test-owner", "--evidence", "ADR.md")
            self.run_cli(project, "activate-domain", *self.target(project), "--domain", "backend", *REVIEW)
            self.run_cli(project, "mark-runtime-ready", *self.target(project))
            self.assertEqual(["ARCHITECTURE.md", "INDEX.md"], self.state(project)["domains"]["backend"]["required_files"])
            self.assertEqual(0, self.validate(project).returncode)
            self.assertFalse((project / "backend").exists())

    def test_registration_tracks_additional_project_leaf(self):
        with runtime_fixture(domains=["backend"]) as project:
            domain = project / "documents/rulers/backend"
            (domain / "CACHING.md").write_bytes((domain / "ARCHITECTURE.md").read_bytes())
            index = domain / "INDEX.md"
            index.write_text(index.read_text() + "\n[Cache](CACHING.md)\n")
            self.run_cli(project, "register-domain-candidate", *self.target(project), "--domain", "backend")
            state = self.state(project)
            self.assertIn("documents/rulers/backend/CACHING.md", state["managed_files"])
            self.assertIn("CACHING.md", state["domains"]["backend"]["required_files"])
            self.assertEqual(0, state["domains"]["backend"]["level"])

    def test_context_safely_reports_malformed_state(self):
        with runtime_fixture() as project:
            path = project / "documents/rulers/RULERS_STATE.json"
            state = self.state(project)
            state["domains"] = "invalid"
            path.write_text(json.dumps(state))
            result = self.validate(project, "context")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(json.loads(result.stdout)["blocked"])

    def test_public_upgrade_preserves_complete_v2_review(self):
        from tests.ai_rulers_test_support import materialize_v2_fixture
        with tempfile.TemporaryDirectory() as td:
            project = Path(td).resolve()
            _, state = materialize_v2_fixture(project, "schema2_runtime_ready.json")
            # The schema fixture describes three domains; materialize the other two too.
            from rulers_lib.state import file_sha256, state_json
            root = project / state["rulers_dir"]
            for domain in ("security", "delivery"):
                file = root / domain / "INDEX.md"
                file.parent.mkdir()
                file.write_bytes((root / "backend/INDEX.md").read_bytes())
                state["managed_files"][file.relative_to(project).as_posix()] = {"ownership": "managed", "rendered_sha256": file_sha256(file)}
            (root / "RULERS_STATE.json").write_text(state_json(state))
            summary = json.loads(self.run_cli(project, "plan", "--project-root", str(project),
                "--rulers-dir", state["rulers_dir"], "--operation", "upgrade").stdout)
            self.run_cli(project, "apply", "--plan", summary["plan_path"], *REVIEW)
            upgraded = json.loads((project / state["rulers_dir"] / "RULERS_STATE.json").read_text())
            self.assertEqual(3, upgraded["schema_version"])
            self.assertEqual("reviewed", upgraded["profile"]["status"])
            self.assertEqual(state["profile"]["content_sha256"], upgraded["profile"]["reviewed_sha256"])

    def test_greenfield_approved_profile_and_candidate_initialize_without_code(self):
        with runtime_fixture() as project:
            self.assertFalse((project / "backend").exists())
            profile = project / "documents/rulers/PROJECT_PROFILE.md"
            candidate = project / "approved.md"
            candidate.write_text(profile.read_text().replace("临时测试项目 | observed", "批准按模块分层 | approved"))
            plan = self.run_cli(project, "plan", *self.target(project), "--operation", "reconcile",
                                "--candidate-profile", "approved.md")
            summary = json.loads(plan.stdout)
            self.assertEqual("reconcile", summary["operation"])
            self.run_cli(project, "apply", "--plan", summary["plan_path"], *REVIEW)
            self.assertIn("批准按模块分层", profile.read_text())
            self.assertEqual(0, self.validate(project).returncode)

    def test_invalid_operation_and_missing_candidate_are_not_ignored(self):
        with runtime_fixture() as project:
            self.run_cli(project, "plan", *self.target(project), "--operation", "invented", success=False)
            self.run_cli(project, "plan", *self.target(project), "--operation", "reconcile",
                         "--candidate-profile", "missing.md", success=False)

    def test_profile_edit_revokes_context_routes(self):
        with runtime_fixture(domains=["backend"]) as project:
            profile = project / "documents/rulers/PROJECT_PROFILE.md"
            profile.write_text(profile.read_text() + "\nUnreviewed change\n")
            context = json.loads(self.validate(project, "context", "--domain", "backend").stdout)
            self.assertTrue(context["blocked"])
            self.assertEqual({}, context["routes"])
            self.assertEqual("", context["profile"]["path"])
            self.run_cli(project, "activate-domain", *self.target(project), "--domain", "backend", *REVIEW, success=False)

    def test_missing_review_is_rejected_and_details_command_works(self):
        with runtime_fixture(domains=["backend"]) as project:
            path = project / "documents/rulers/RULERS_STATE.json"
            state = self.state(project)
            del state["domains"]["backend"]["review"]
            path.write_text(json.dumps(state))
            self.assertNotEqual(0, self.validate(project).returncode)
            context = json.loads(self.validate(project, "context", "--domain", "backend").stdout)
            self.assertEqual({}, context["routes"])
            import shlex
            diagnostic = subprocess.run(shlex.split(context["details_command"]), cwd=project, capture_output=True, text=True)
            self.assertEqual(1, diagnostic.returncode, diagnostic.stderr)
            self.assertIn("VR014", diagnostic.stdout)

    def test_public_writers_respect_lock(self):
        with runtime_fixture(domains=["backend"]) as project:
            before = (project / "documents/rulers/RULERS_STATE.json").read_bytes()
            with maintenance_lock(layout=resolve_layout(project, "documents/rulers")):
                for command, extra in (("activate-domain", ("--domain", "backend", *REVIEW)),
                                       ("register-domain-candidate", ("--domain", "backend")),
                                       ("review-profile", REVIEW), ("mark-runtime-ready", ())):
                    self.run_cli(project, command, *self.target(project), *extra, success=False)
            self.assertEqual(before, (project / "documents/rulers/RULERS_STATE.json").read_bytes())

    def test_rules_add_delete_reactivate_and_upgrade_preserves_customization(self):
        with runtime_fixture(domains=["backend"]) as project:
            target = project / "documents/rulers/backend"
            candidate = project / "rule-draft"
            shutil.copytree(target, candidate)
            (candidate / "OBSERVABILITY.md").unlink()
            (candidate / "CACHING.md").write_text((candidate / "ARCHITECTURE.md").read_text().replace("ARCHITECTURE", "CACHING"))
            index = candidate / "INDEX.md"
            index.write_text("\n".join(line for line in index.read_text().splitlines() if "OBSERVABILITY.md" not in line)
                             + "\n- [Cache](documents/rulers/backend/CACHING.md)\n")
            self.run_cli(project, "rules-plan", *self.target(project), "--domain", "backend", "--candidate-dir", "rule-draft",
                         "--reason", "Cache policy replaces unused observability guidance", "--output", "rule-plan.json")
            self.run_cli(project, "rules-apply", "--plan", "rule-plan.json", "--reviewed-by", "test-owner", "--evidence", "test-only")
            repeated = self.run_cli(project, "rules-apply", "--plan", "rule-plan.json", "--reviewed-by", "test-owner", "--evidence", "test-only")
            self.assertEqual([], json.loads(repeated.stdout)["changed_files"])
            self.assertFalse((target / "OBSERVABILITY.md").exists())
            state = self.state(project)
            self.assertIn("CACHING.md", state["domains"]["backend"]["required_files"])
            self.assertIn("OBSERVABILITY.md", state["domains"]["backend"]["removed_files"])
            self.assertEqual(0, state["domains"]["backend"]["level"])
            self.run_cli(project, "activate-domain", *self.target(project), "--domain", "backend", *REVIEW)
            expected = (target / "CACHING.md").read_bytes()
            summary = json.loads(self.run_cli(project, "plan", *self.target(project), "--operation", "upgrade", "--policy", "project-native").stdout)
            self.run_cli(project, "apply", "--plan", summary["plan_path"], *REVIEW)
            self.assertEqual(expected, (target / "CACHING.md").read_bytes())
            self.assertFalse((target / "OBSERVABILITY.md").exists())
            self.assertFalse((project / "documents/rulers/core/GIT_COMMIT_CONVENTION.md").exists())
            self.assertEqual(0, self.validate(project).returncode)
            bundle = self.validate(project, "load", "--domain", "backend", "--rule", "backend/CACHING.md")
            self.assertEqual(0, bundle.returncode, bundle.stderr)
            self.assertIn("documents/rulers/backend/CACHING.md", json.loads(bundle.stdout)["files"])

    def test_invalid_rule_links_roll_back_all_changes(self):
        with runtime_fixture(domains=["backend"]) as project:
            target = project / "documents/rulers/backend"
            draft = project / "draft"
            shutil.copytree(target, draft)
            (draft / "INDEX.md").write_text((draft / "INDEX.md").read_text() + "\n[Missing](missing.md)\n")
            before = {p.relative_to(project).as_posix(): p.read_bytes() for p in (project / "documents/rulers").rglob("*") if p.is_file() and ".plans" not in p.parts}
            self.run_cli(project, "rules-plan", *self.target(project), "--domain", "backend", "--candidate-dir", "draft", "--reason", "test-invalid-link", "--output", "rule-plan.json")
            self.run_cli(project, "rules-apply", "--plan", "rule-plan.json", "--reviewed-by", "test-owner", "--evidence", "test-only", success=False)
            for path, content in before.items():
                self.assertEqual(content, (project / path).read_bytes(), path)

    def test_repair_restores_core_and_repeated_apply_is_unchanged(self):
        with runtime_fixture() as project:
            path = project / "documents/rulers/core/WORKFLOW.md"
            original = path.read_bytes()
            path.write_bytes(original + b"\naccidental edit\n")
            summary = json.loads(self.run_cli(project, "plan", *self.target(project), "--operation", "repair",
                "--resolution", "documents/rulers/core/WORKFLOW.md=restore-managed").stdout)
            self.run_cli(project, "apply", "--plan", summary["plan_path"], *REVIEW)
            self.assertEqual(original, path.read_bytes())
            repeated = json.loads(self.run_cli(project, "apply", "--plan", summary["plan_path"], *REVIEW).stdout)
            self.assertEqual([], repeated["changed_files"])

    def test_existing_claude_is_integrated_on_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td).resolve()
            (project / "CLAUDE.md").write_text("# Keep team instructions\n")
            summary = json.loads(self.run_cli(project, "plan", *self.target(project), "--policy", "project-native").stdout)
            self.run_cli(project, "apply", "--plan", summary["plan_path"])
            claude = (project / "CLAUDE.md").read_text()
            self.assertIn("Keep team instructions", claude)
            self.assertEqual(1, claude.count("ai-rulers-init:begin"))


if __name__ == "__main__":
    unittest.main()
