"""Readiness candidates at the public consolidated initialization boundary."""

import base64
import hashlib
import json
import unittest

from tests import test_module_workflows as module_fixtures
from scripts.runtime_fixture import REVIEW


class InitializationReadinessTest(unittest.TestCase):
    def setUp(self):
        self.fixture = module_fixtures.ModuleWorkflowTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.workspace
        self.rulers_dir = "documents/rulers"

    def write_json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return relative

    def candidate(self, domain, name="workspace"):
        relative = f".rulers-work/candidates/{name}-{domain}"
        directory = self.root / relative
        directory.mkdir(parents=True, exist_ok=True)
        metadata = "```yaml\nmetadata:\n  applies_to:\n    - '**/*'\n  trigger_keywords:\n    - synthetic\n  must_load_with: []\n```\n"
        (directory / "INDEX.md").write_text("# Synthetic rules\n" + metadata + "\n[Coverage](COVERAGE.md)\n")
        (directory / "COVERAGE.md").write_text("# Synthetic coverage\n" + metadata + "\nAutomated test-only rule coverage.\n")
        return relative

    def source(self, name="workspace", references=None):
        rule = f"{self.rulers_dir}/delivery/COVERAGE.md"
        return self.write_json(f".rulers-work/candidates/{name}-readiness.json", references or {
            "security": [rule], "quality": [rule], "rollback": [rule],
        })

    def plan(self, projects):
        settings = self.write_json(".rulers-work/readiness-candidates.json", {"projects": projects})
        summary = json.loads(self.fixture.cli(self.root, "init-plan", "--candidates", settings).stdout)
        plan = json.loads((self.root / summary["plan_path"]).read_text())
        return summary, plan

    def apply(self, summary, success=True):
        return self.fixture.cli(self.root, "init-apply", "--plan", summary["plan_path"],
            "--reviewed-by", "synthetic-initialization-auditor",
            "--evidence", "automated-test-only-not-human-approval", success=success)

    def state(self, project=None):
        return json.loads(((project or self.root) / self.rulers_dir / "RULERS_STATE.json").read_text())

    def test_repeated_previews_do_not_publish_disposable_maintenance_records(self):
        candidate = self.candidate("delivery")
        projects = {"workspace": {"domains": {"delivery": candidate}}}
        _, first = self.plan(projects)
        summary, second = self.plan(projects)
        self.assertEqual(first, second)
        projected = json.loads(base64.b64decode(first["changes"]["workspace"]["files"][self.rulers_dir + "/RULERS_STATE.json"]))
        self.assertNotIn("maintenance_execution", projected)
        self.apply(summary)
        self.assertNotIn("maintenance_execution", self.state())

    def test_initialization_keeps_existing_target_maintenance_record(self):
        backend = self.candidate("backend")
        self.fixture.cli(self.root, "rules-plan", "--project-root", str(self.root),
            "--domain", "backend", "--candidate-dir", backend, "--reason", "synthetic prior maintenance",
            "--output", ".rulers-work/prior-rule-plan.json")
        self.fixture.cli(self.root, "rules-apply", "--plan", ".rulers-work/prior-rule-plan.json",
            "--reviewed-by", "synthetic-prior-auditor", "--evidence", "test-only")
        prior = self.state()["maintenance_execution"]
        delivery = self.candidate("delivery")
        summary, plan = self.plan({"workspace": {"domains": {"delivery": delivery}}})
        projected = json.loads(base64.b64decode(plan["changes"]["workspace"]["files"][self.rulers_dir + "/RULERS_STATE.json"]))
        self.assertEqual(prior, projected["maintenance_execution"])
        self.apply(summary)
        self.assertEqual(prior, self.state()["maintenance_execution"])

    def test_consolidated_review_materializes_bound_coverage_and_repeat_is_noop(self):
        candidate, source = self.candidate("delivery"), self.source()
        projects = {"workspace": {"domains": {"delivery": candidate}, "readiness": {"delivery": source}}}
        before = (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes()
        summary, plan = self.plan(projects)
        self.assertEqual("review", summary["status"])
        self.assertEqual([], summary["preparation"])
        self.assertEqual(before, (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes())
        expected_source_hash = "sha256:" + hashlib.sha256((self.root / source).read_bytes()).hexdigest()
        self.assertEqual(expected_source_hash, plan["candidate_inputs"][source])
        self.assertEqual(expected_source_hash, plan["readiness_inputs"]["workspace"]["delivery"]["sha256"])
        review = (self.root / summary["review_path"]).read_text()
        self.assertIn(source, review)
        self.assertIn(expected_source_hash, review)
        self.assertIn("documents/rulers/delivery/COVERAGE.md", review)
        self.assertIn('"level3_ready": true', review)
        projected = json.loads(base64.b64decode(plan["changes"]["workspace"]["files"][self.rulers_dir + "/RULERS_STATE.json"]))
        declaration = projected["domains"]["delivery"]["review"]["readiness"]
        self.assertNotIn("review", declaration["bindings"]["delivery"])
        self.apply(summary)
        actual = self.state()["domains"]["delivery"]
        self.assertEqual("synthetic-initialization-auditor", actual["review"]["reviewed_by"])
        self.assertEqual("automated-test-only-not-human-approval", actual["review"]["evidence"])
        self.assertEqual(declaration, actual["review"]["readiness"])
        context = json.loads(self.fixture.validate_module(self.root, "--mode", "context", "--domain", "delivery").stdout)
        self.assertFalse(context["blocked"])
        self.assertIn("delivery", context["level3_ready"])
        installed = (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes()
        again, _ = self.plan(projects)
        self.assertEqual("noop", again["status"])
        self.assertEqual([], json.loads(self.apply(again).stdout)["changed_files"])
        self.assertEqual(installed, (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes())

    def test_coverage_is_compiled_after_all_candidate_owners_are_active(self):
        delivery, backend = self.candidate("delivery"), self.candidate("backend")
        source = self.source(references={
            "security": [self.rulers_dir + "/backend/COVERAGE.md"],
            "quality": [self.rulers_dir + "/delivery/COVERAGE.md"],
            "rollback": [self.rulers_dir + "/delivery/COVERAGE.md"],
        })
        summary, _ = self.plan({"workspace": {"domains": {"delivery": delivery, "backend": backend},
            "readiness": {"delivery": source}}})
        self.assertEqual([], summary["preparation"])
        self.apply(summary)
        self.assertTrue(self.state()["domains"]["delivery"]["level3_ready"])
        self.assertEqual(2, self.state()["domains"]["backend"]["level"])

    def test_no_declaration_preserves_level_two_without_ready(self):
        summary, _ = self.plan({"workspace": {"domains": {"delivery": self.candidate("delivery")}}})
        self.apply(summary)
        domain = self.state()["domains"]["delivery"]
        self.assertEqual(2, domain["level"])
        self.assertFalse(domain["level3_ready"])
        self.assertNotIn("readiness", domain["review"])

    def test_readiness_requires_an_explicit_matching_domain_candidate(self):
        source = self.source()
        self.write_json(".rulers-work/readiness-candidates.json", {"projects": {
            "workspace": {"readiness": {"delivery": source}},
        }})
        result = self.fixture.cli(self.root, "init-plan", "--candidates", ".rulers-work/readiness-candidates.json", success=False)
        self.assertIn("explicit domain candidates", result.stderr)

    def test_source_rejects_approval_fields_and_unsafe_rule_paths(self):
        candidate, source = self.candidate("delivery"), self.source()
        source_path = self.root / source
        value = json.loads(source_path.read_text())
        value["reviewed_by"] = "forged-source-review"
        source_path.write_text(json.dumps(value))
        settings = self.write_json(".rulers-work/readiness-candidates.json", {"projects": {
            "workspace": {"domains": {"delivery": candidate}, "readiness": {"delivery": source}},
        }})
        before = (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes()
        result = self.fixture.cli(self.root, "init-plan", "--candidates", settings, success=False)
        self.assertIn("only security, quality and rollback", result.stderr)
        self.source(references={"security": ["../outside.md"], "quality": [self.rulers_dir + "/delivery/COVERAGE.md"],
            "rollback": [self.rulers_dir + "/delivery/COVERAGE.md"]})
        summary, _ = self.plan({"workspace": {"domains": {"delivery": candidate}, "readiness": {"delivery": source}}})
        self.assertEqual("preparation", summary["status"])
        self.assertTrue(any("canonical relative Markdown paths" in item["reason"] for item in summary["preparation"]))
        self.assertEqual(before, (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes())

    def test_source_or_coverage_changes_refuse_the_old_approval(self):
        candidate, source = self.candidate("delivery"), self.source()
        projects = {"workspace": {"domains": {"delivery": candidate}, "readiness": {"delivery": source}}}
        before = (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes()
        for relative in (source, candidate + "/COVERAGE.md"):
            with self.subTest(relative=relative):
                summary, _ = self.plan(projects)
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n ")
                result = self.apply(summary, success=False)
                self.assertIn("inputs changed", result.stderr)
                self.assertEqual(before, (self.root / self.rulers_dir / "RULERS_STATE.json").read_bytes())
                path.write_bytes(original)

    def test_module_uses_local_rule_coordinates_and_does_not_propagate_ready(self):
        child = self.fixture.add_submodule("server")
        candidate, source = self.candidate("delivery", "server"), self.source("server")
        profile = ".rulers-work/candidates/server-profile.md"
        (self.root / profile).write_bytes((self.root / self.rulers_dir / "PROJECT_PROFILE.md").read_bytes())
        manifest = self.write_json(".rulers-work/candidates/server-export.json", {
            "version": 1, "rules": [{"path": "delivery/INDEX.md", "domain": "delivery"},
                {"path": "delivery/COVERAGE.md", "domain": "delivery"}],
            "profile_scopes": ["core", "delivery"], "commands": [], "evidence": ["README.md"],
        })
        summary, _ = self.plan({"server": {"profile": profile, "domains": {"delivery": candidate},
            "export_manifest": manifest, "readiness": {"delivery": source}}})
        self.assertEqual([], summary["preparation"])
        self.apply(summary)
        domain = self.state(child)["domains"]["delivery"]
        self.assertTrue(domain["level3_ready"])
        self.assertEqual("documents/rulers/delivery/COVERAGE.md", domain["review"]["readiness"]["coverage"]["security"][0]["path"])
        self.assertEqual("synthetic-initialization-auditor", domain["review"]["reviewed_by"])
        self.assertNotIn("readiness", self.state()["modules"]["server"]["review"])
        loaded = self.fixture.validate_module(self.root, "--mode", "load", "--module", "server", "--domain", "delivery",
            "--rule", "delivery/COVERAGE.md").stdout
        self.assertIn("Automated test-only rule coverage", loaded)

    def test_custom_rule_directory_binds_actual_paths(self):
        custom = self.fixture.root / "custom-project"
        custom.mkdir()
        self.root, self.rulers_dir = custom, "custom/rules"
        summary = json.loads(self.fixture.cli(custom, "plan", "--project-root", str(custom),
            "--rulers-dir", self.rulers_dir).stdout)
        self.fixture.cli(custom, "apply", "--plan", str(custom / summary["plan_path"]))
        self.fixture.cli(custom, "review-profile", "--project-root", str(custom), "--rulers-dir", self.rulers_dir, *REVIEW)
        self.fixture.cli(custom, "mark-runtime-ready", "--project-root", str(custom), "--rulers-dir", self.rulers_dir)
        candidate, source = self.candidate("delivery"), self.source()
        summary, _ = self.plan({"workspace": {"domains": {"delivery": candidate}, "readiness": {"delivery": source}}})
        self.apply(summary)
        domain = self.state()["domains"]["delivery"]
        self.assertTrue(domain["level3_ready"])
        self.assertEqual("custom/rules/delivery/COVERAGE.md", domain["review"]["readiness"]["coverage"]["quality"][0]["path"])


if __name__ == "__main__":
    unittest.main()
