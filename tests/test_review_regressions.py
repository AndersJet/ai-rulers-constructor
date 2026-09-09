"""Regression cases from the two-axis review, using isolated target projects."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.runtime_fixture import runtime_fixture, REVIEW
from tests.ai_rulers_test_support import run_cli


class ReviewRegressionTest(unittest.TestCase):
    def cli(self, project, *args, success=True):
        result = run_cli(*args, cwd=project)
        if success:
            self.assertEqual(0, result.returncode, result.stderr)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout)
        return result

    def load(self, project, *args):
        return subprocess.run([sys.executable, str(project / "documents/rulers/scripts/validate_rulers.py"),
                               "--mode", "load", "--project-root", str(project), *args],
                              cwd=project, text=True, capture_output=True)

    def state(self, project):
        return json.loads((project / "documents/rulers/RULERS_STATE.json").read_text())

    def test_shared_profile_scope_syntax_is_preserved_in_load(self):
        from rulers_lib.reconcile import parse_profile
        from rulers_lib.rule_loading import build_load_bundle
        from rulers_lib.validation import inspect_project
        from rulers_lib.state import file_sha256, state_json
        with runtime_fixture(domains=["backend", "security"]) as project:
            profile = project / "documents/rulers/PROJECT_PROFILE.md"
            original = profile.read_text()
            for separator in (", ", "， ", "<br>", "<br />"):
                with self.subTest(separator=separator):
                    scope = f"security{separator}backend"
                    text = original.replace("| 临时测试项目 | observed", "| SHARED_BOUNDARY | approved").replace("| core | high |", f"| {scope} | high |")
                    text = text.replace(f"| {scope} | high |\n", f"| {scope} | high |\n| SECURITY_ONLY | approved | ADR.md | security | high |\n")
                    text += f"| SHARED_QUESTION | Need decision | {scope} | owner |\n"
                    parsed = parse_profile(text, allowed_scopes={"core", "backend", "security"})
                    self.assertEqual(("backend", "security"), next(r for r in parsed.records if r.content == "SHARED_BOUNDARY").scopes)
                    profile.write_text(text)
                    state = self.state(project)
                    state["profile"]["reviewed_sha256"] = file_sha256(profile)
                    (project / "documents/rulers/RULERS_STATE.json").write_text(state_json(state))
                    bundle = build_load_bundle(inspect_project(project_root=project, rulers_dir="documents/rulers"), domains=["backend"])
                    self.assertIn("SHARED_BOUNDARY", bundle["content"])
                    self.assertIn("SHARED_QUESTION", bundle["content"])
                    self.assertNotIn("SECURITY_ONLY", bundle["content"])

    def test_new_leaf_without_index_link_cannot_be_adopted(self):
        with runtime_fixture(domains=["backend"]) as project:
            target = project / "documents/rulers/backend"
            candidate = project / "draft"
            shutil.copytree(target, candidate)
            (candidate / "ORPHAN.md").write_bytes((candidate / "TESTING.md").read_bytes())
            before = (project / "documents/rulers/RULERS_STATE.json").read_bytes()
            self.cli(project, "rules-plan", "--domain", "backend", "--candidate-dir", "draft", "--reason", "review-regression", "--output", "plan.json")
            self.cli(project, "rules-apply", "--plan", "plan.json", "--reviewed-by", "test-owner", "--evidence", "test-only", success=False)
            self.assertFalse((target / "ORPHAN.md").exists())
            self.assertEqual(before, (project / "documents/rulers/RULERS_STATE.json").read_bytes())

    def test_web_registration_cannot_adopt_draft_app_rules(self):
        with runtime_fixture(domains=["frontend-web", "frontend-app"]) as project:
            app_rule = project / "documents/rulers/frontend/app/develop/TESTING.md"
            app_rule.write_text(app_rule.read_text() + "\nUNREVIEWED_APP_RULE\n")
            self.cli(project, "register-domain-candidate", "--domain", "frontend-app")
            app_state = copy.deepcopy(self.state(project)["domains"]["frontend-app"])
            app_inventory = {p: v for p, v in self.state(project)["managed_files"].items() if p.startswith("documents/rulers/frontend/app/")}
            web_rule = project / "documents/rulers/frontend/web/develop/TESTING.md"
            web_rule.write_text(web_rule.read_text() + "\nWeb clarification\n")
            self.cli(project, "register-domain-candidate", "--domain", "frontend-web")
            self.cli(project, "activate-domain", "--domain", "frontend-web", *REVIEW)
            state = self.state(project)
            self.assertFalse(any(name.startswith("app/") for name in state["domains"]["frontend-web"]["required_files"]))
            self.assertEqual(app_state, state["domains"]["frontend-app"])
            self.assertEqual(app_inventory, {p: v for p, v in state["managed_files"].items() if p.startswith("documents/rulers/frontend/app/")})
            loaded = self.load(project, "--domain", "frontend-web", "--rule", "frontend/app/develop/TESTING.md")
            self.assertNotEqual(0, loaded.returncode)
            self.assertNotIn("UNREVIEWED_APP_RULE", loaded.stdout)

    def test_web_maintenance_preserves_installed_app_subtree(self):
        with runtime_fixture(domains=["frontend-web", "frontend-app"]) as project:
            target = project / "documents/rulers/frontend"
            candidate = project / "draft"
            shutil.copytree(target, candidate)
            app_before = {p.relative_to(target).as_posix(): p.read_bytes() for p in (target / "app").rglob("*.md")}
            state_before = self.state(project)
            changed = candidate / "web/develop/TESTING.md"
            changed.write_text(changed.read_text() + "\nWeb-only requirement\n")
            self.cli(project, "rules-plan", "--domain", "frontend-web", "--candidate-dir", "draft", "--reason", "web-only change", "--output", "plan.json")
            self.cli(project, "rules-apply", "--plan", "plan.json", "--reviewed-by", "test-owner", "--evidence", "test-only")
            self.assertIn("Web-only requirement", (target / "web/develop/TESTING.md").read_text())
            self.assertEqual(app_before, {p.relative_to(target).as_posix(): p.read_bytes() for p in (target / "app").rglob("*.md")})
            self.assertEqual(state_before["domains"]["frontend-app"], self.state(project)["domains"]["frontend-app"])

    def test_legacy_web_inventory_cannot_load_app_owned_files(self):
        with runtime_fixture(domains=["frontend-app", "frontend-web"]) as project:
            state = self.state(project)
            self.assertFalse(any(name.startswith("app/") for name in state["domains"]["frontend-web"]["required_files"]))
            state["domains"]["frontend-web"]["required_files"].append("app/develop/TESTING.md")
            state["domains"]["frontend-app"].update(level=0, review_status="draft")
            (project / "documents/rulers/RULERS_STATE.json").write_text(json.dumps(state))
            result = self.load(project, "--domain", "frontend-web", "--rule", "frontend/app/develop/TESTING.md")
            self.assertNotEqual(0, result.returncode)
            self.cli(project, "register-domain-candidate", "--domain", "frontend-web")
            self.assertFalse(any(name.startswith("app/") for name in self.state(project)["domains"]["frontend-web"]["required_files"]))

    def test_parent_candidate_can_omit_but_not_change_app(self):
        with runtime_fixture(domains=["frontend-web", "frontend-app"]) as project:
            target = project / "documents/rulers/frontend"
            candidate = project / "draft"
            shutil.copytree(target, candidate)
            shutil.rmtree(candidate / "app")
            web = candidate / "web/develop/TESTING.md"
            web.write_text(web.read_text() + "\nWeb-only requirement\n")
            app_before = {p.relative_to(target).as_posix(): p.read_bytes() for p in (target / "app").rglob("*.md")}
            self.cli(project, "rules-plan", "--domain", "frontend-web", "--candidate-dir", "draft", "--reason", "web-only", "--output", "plan.json")
            self.cli(project, "rules-apply", "--plan", "plan.json", "--reviewed-by", "test-owner", "--evidence", "test-only")
            self.assertEqual(app_before, {p.relative_to(target).as_posix(): p.read_bytes() for p in (target / "app").rglob("*.md")})
            shutil.copytree(target / "app", candidate / "app")
            app = candidate / "app/develop/TESTING.md"
            app.write_text(app.read_text() + "\nWrong domain edit\n")
            self.cli(project, "rules-plan", "--domain", "frontend-web", "--candidate-dir", "draft", "--reason", "must reject", "--output", "bad-plan.json", success=False)

    def test_registration_rejects_unlinked_leaf(self):
        with runtime_fixture(domains=["backend"]) as project:
            root = project / "documents/rulers"
            (root / "backend/ORPHAN.md").write_bytes((root / "backend/TESTING.md").read_bytes())
            before = (root / "RULERS_STATE.json").read_bytes()
            self.cli(project, "register-domain-candidate", "--domain", "backend", success=False)
            self.assertEqual(before, (root / "RULERS_STATE.json").read_bytes())

    def test_fresh_preserves_bound_candidate_without_activating_it(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td).resolve()
            candidate = project / "approved.md"
            candidate.write_text("# 项目画像\n\n## 项目身份\nGreenfield\n\n## 命令\n\n"
                "## 当前有效事实与约束\n\n| 内容 | 依据类型 | 证据 | 作用域 | 置信度 |\n| --- | --- | --- | --- | --- |\n"
                "| APPROVED_BOUNDARY | approved | ADR.md | core | high |\n\n"
                "## 阻塞性未决问题\n\n| 问题 | 重要原因 | 作用域 | 必需审阅人 |\n| --- | --- | --- | --- |\n")
            summary = json.loads(self.cli(project, "plan", "--candidate-profile", "approved.md").stdout)
            self.cli(project, "apply", "--plan", summary["plan_path"])
            self.assertEqual(candidate.read_bytes(), (project / "documents/rulers/PROJECT_PROFILE.md").read_bytes())
            self.assertEqual("draft", self.state(project)["profile"]["status"])
            self.assertEqual(0, self.state(project)["domains"]["core"]["level"])
