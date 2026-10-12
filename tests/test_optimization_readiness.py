"""Production-rule review coverage in disposable projects; no operation approval."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.runtime_fixture import runtime_fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/ai-rulers-init/scripts"))

from rulers_lib.paths import resolve_layout
from rulers_lib.readiness import ReadinessError, compile_readiness, evaluate_readiness
from rulers_lib.validation import inspect_project


class OptimizationReadinessTest(unittest.TestCase):
    def fixture(self, *, rulers_dir="documents/rulers"):
        project = self.enterContext(runtime_fixture(rulers_dir=rulers_dir, domains=("security", "delivery")))
        layout = resolve_layout(project, rulers_dir)
        state = json.loads((layout.rulers_root / "RULERS_STATE.json").read_text())
        source = {"security": [f"{rulers_dir}/security/SECRETS.md"],
                  "quality": [f"{rulers_dir}/delivery/CI.md"],
                  "rollback": [f"{rulers_dir}/delivery/ROLLBACK.md"]}
        return layout, state, source

    def save(self, layout, state):
        (layout.rulers_root / "RULERS_STATE.json").write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return inspect_project(project_root=layout.project_root, rulers_dir=layout.rulers_dir)

    def assessed(self, layout, state, source):
        declaration = compile_readiness(layout, state, "delivery", source)
        state["domains"]["delivery"]["review"]["readiness"] = declaration
        return self.save(layout, state)

    def test_legacy_numeric_flags_do_not_assess_production_rules(self):
        layout, state, _ = self.fixture()
        state["domains"]["delivery"].update(level3_ready=True, readiness_level=3)
        result = evaluate_readiness(self.save(layout, state), "delivery")
        self.assertEqual({"ready": False, "status": "not_assessed", "reasons": ["no_declaration"]}, result)

    def test_valid_bound_coverage_survives_real_review_identity_materialization(self):
        layout, state, source = self.fixture()
        inspection = self.assessed(layout, state, source)
        self.assertEqual({"ready": True, "status": "ready", "reasons": []}, evaluate_readiness(inspection, "delivery"))

        for domain in ("security", "delivery"):
            state["domains"][domain]["review"].update(reviewed_by="another-test-owner", reviewed_at="2026-10-06T10:00:00+00:00",
                                                       evidence="synthetic-materialized-review-only")
        inspection = self.save(layout, state)
        before = copy.deepcopy(inspection.state)
        self.assertTrue(evaluate_readiness(inspection, "delivery")["ready"])
        self.assertEqual(before, inspection.state)

    def test_custom_rule_root_and_one_adopted_file_can_cover_all_roles(self):
        layout, state, _ = self.fixture(rulers_dir="custom/rule-set")
        path = "custom/rule-set/security/SECRETS.md"
        source = {role: [path, path] for role in ("security", "quality", "rollback")}
        compiled = compile_readiness(layout, state, "delivery", source)
        canonical = compile_readiness(layout, state, "delivery", {role: [path] for role in source})
        self.assertEqual(canonical, compiled)
        self.assertTrue(evaluate_readiness(self.assessed(layout, state, source), "delivery")["ready"])

    def test_source_rejects_approval_fields_empty_roles_and_unadopted_paths(self):
        layout, state, source = self.fixture()
        invalid = [
            {**source, "ready": True}, {**source, "reviewed_by": "fake-owner"},
            {**source, "security": []}, {**source, "rollback": "documents/rulers/delivery/ROLLBACK.md"},
            {**source, "quality": ["docs/CI.md"]},
            {**source, "quality": ["documents/rulers/delivery/UNADOPTED.md"]},
            {**source, "quality": ["../outside.md"]},
            {**source, "quality": [str(layout.rulers_root / "delivery/CI.md")]},
        ]
        (layout.rulers_root / "delivery/UNADOPTED.md").write_text("# Exists without adoption\n")
        before = copy.deepcopy(state)
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                compile_readiness(layout, state, "delivery", candidate)
        self.assertEqual(before, state)

    def test_internal_symbolic_link_cannot_supply_readiness_evidence(self):
        layout, state, source = self.fixture()
        leaf = layout.rulers_root / "security/SECRETS.md"
        leaf.unlink()
        leaf.symlink_to("AUTHORIZATION.md")
        with self.assertRaises(ReadinessError) as rejected:
            compile_readiness(layout, state, "delivery", source)
        self.assertEqual("reference_unsafe", rejected.exception.code)

    def test_candidate_can_reference_new_target_leaf_but_not_external_unadopted_leaf(self):
        layout, state, source = self.fixture()
        target = state["domains"]["delivery"]
        hashes = {f"{layout.rulers_dir}/delivery/{name}": state["managed_files"][f"{layout.rulers_dir}/delivery/{name}"]["rendered_sha256"]
                  for name in target["required_files"]}
        new_path = "documents/rulers/delivery/PRODUCTION_POLICY.md"
        new_hash = "sha256:" + hashlib.sha256(b"Synthetic new production rule\n").hexdigest()
        hashes[new_path] = new_hash
        source = {role: [new_path] for role in source}
        target.update(level=0, review_status="draft", review={})
        compiled = compile_readiness(layout, state, "delivery", source, candidate_hashes=hashes)
        self.assertEqual(new_hash, compiled["coverage"]["rollback"][0]["sha256"])
        self.assertFalse((layout.project_root / new_path).exists())
        self.assertEqual(set(hashes), set(compiled["bindings"]["delivery"]["rules"]))
        with self.assertRaises(ValueError):
            compile_readiness(layout, state, "delivery", {**source, "security": ["documents/rulers/security/UNADOPTED.md"]},
                              candidate_hashes=hashes)
        with self.assertRaises(ValueError):
            compile_readiness(layout, state, "delivery", source,
                              candidate_hashes={**hashes, "documents/rulers/security/UNADOPTED.md": new_hash})

    def test_external_coverage_drift_is_advisory_for_an_independent_ci_domain(self):
        layout, state, source = self.fixture()
        state["domains"]["delivery"]["requires_active"] = []
        self.assessed(layout, state, source)
        path = layout.rulers_root / "security/SECRETS.md"
        path.write_text(path.read_text() + "\nUnreviewed external rule change\n")
        inspection = inspect_project(project_root=layout.project_root, rulers_dir=layout.rulers_dir)
        before_issues = inspection.issues
        self.assertNotIn("delivery", inspection.invalid_domains)
        result = evaluate_readiness(inspection, "delivery")
        self.assertFalse(result["ready"])
        self.assertEqual("unmet", result["status"])
        self.assertEqual(["owner_invalid"], result["reasons"])
        self.assertEqual(before_issues, inspection.issues)

    def test_global_scope_profile_and_missing_owner_review_cannot_be_ready(self):
        layout, state, source = self.fixture()
        inspection = self.assessed(layout, state, source)
        for invalid in (replace(inspection, global_blocked=True), replace(inspection, profile_valid=False),
                        replace(inspection, invalid_domains=frozenset({"delivery"})),
                        replace(inspection, invalid_domains=frozenset({"security"}))):
            with self.subTest(invalid=invalid.invalid_domains):
                self.assertEqual("unmet", evaluate_readiness(invalid, "delivery")["status"])
        state["domains"]["security"]["review"]["evidence"] = None
        with self.assertRaises(ValueError):
            compile_readiness(layout, state, "delivery", source)

    def test_dependency_change_and_tampered_declaration_revoke_readiness(self):
        layout, state, source = self.fixture()
        state["domains"]["delivery"]["requires_active"] = ["security"]
        self.assessed(layout, state, source)
        state["domains"]["delivery"]["requires_active"] = []
        result = evaluate_readiness(self.save(layout, state), "delivery")
        self.assertEqual(["binding_changed"], result["reasons"])
        state["domains"]["delivery"]["review"]["readiness"]["coverage"]["quality"][0]["sha256"] = "sha256:" + "0" * 64
        result = evaluate_readiness(self.save(layout, state), "delivery")
        self.assertEqual(["declaration_invalid"], result["reasons"])


if __name__ == "__main__":
    unittest.main()
