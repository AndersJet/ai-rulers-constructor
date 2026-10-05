"""Single-approval domain maintenance in disposable, synthetic projects."""
from __future__ import annotations

import copy
import json
import os
import shutil
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from scripts.runtime_fixture import SKILL_ROOT, runtime_fixture

sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from rulers_lib import rule_maintenance
from rulers_lib.paths import resolve_layout
from rulers_lib.readiness import evaluate_readiness
from rulers_lib.state import file_sha256, state_json
from rulers_lib.transactions import inspect_incomplete_transaction
from rulers_lib.validation import inspect_project


REVIEWER = "synthetic-maintenance-auditor"
EVIDENCE = "automated-test-only-not-human-approval"
REVIEW = ("--reviewed-by", REVIEWER, "--evidence", EVIDENCE)
RULERS_DIR = "documents/rulers"


class OptimizationMaintenanceTest(unittest.TestCase):
    def fixture(self, *domains):
        return self.enterContext(runtime_fixture(domains=domains or ("backend",)))

    def state_path(self, project):
        return project / RULERS_DIR / "RULERS_STATE.json"

    def state(self, project):
        return json.loads(self.state_path(project).read_text(encoding="utf-8"))

    def save(self, project, state):
        self.state_path(project).write_text(state_json(state), encoding="utf-8")

    def target(self, project, domain="backend"):
        return project / RULERS_DIR / self.state(project)["domains"][domain]["target_dir"]

    def candidate(self, project, domain="backend", *, name="rule-candidate", change=True):
        candidate = project / name
        shutil.copytree(self.target(project, domain), candidate)
        if change:
            leaf = next(path for path in sorted(candidate.rglob("*.md")) if path.name != "INDEX.md")
            leaf.write_text(leaf.read_text(encoding="utf-8") + "\nSynthetic reviewed maintenance change.\n", encoding="utf-8")
        return name

    def source(self, project, *, value=None, name="readiness.json"):
        rule = f"{RULERS_DIR}/delivery/CI.md"
        value = value or {role: [rule] for role in ("security", "quality", "rollback")}
        (project / name).write_text(json.dumps(value), encoding="utf-8")
        return name

    def plan(self, project, *, domain="backend", candidate="rule-candidate", activate=True,
             source=None, skill_root=SKILL_ROOT):
        return rule_maintenance.plan_rules_change(
            skill_root=skill_root, project_root=project, rulers_dir=RULERS_DIR,
            domain=domain, candidate_dir=candidate,
            reason="Synthetic regression evidence; automated tests only",
            activate_on_apply=activate, readiness_source=source,
        )

    def apply(self, plan, *, reviewer=REVIEWER, evidence=EVIDENCE, skill_root=SKILL_ROOT):
        return rule_maintenance.apply_rules_change(
            plan=plan, skill_root=skill_root, reviewed_by=reviewer, evidence=evidence,
        )

    def cli(self, project, *args, success=True, script="rulers_init.py"):
        result = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / script), *args],
            cwd=project, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True,
        )
        if success:
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout)
        return result

    def cli_plan(self, project, *, activate=False, source=None, domain="backend", candidate="rule-candidate"):
        args = ["rules-plan", "--project-root", str(project), "--domain", domain,
                "--candidate-dir", candidate, "--reason", "Synthetic CLI regression", "--output", "rule-plan.json"]
        if activate:
            args.append("--activate-on-apply")
        if source:
            args.extend(("--readiness-source", source))
        self.cli(project, *args)
        return json.loads((project / "rule-plan.json").read_text(encoding="utf-8"))

    def snapshot(self, project, *, times=False):
        """Compare user-visible runtime files, excluding transaction artifacts."""
        paths = [project / "AGENTS.md"] + list((project / RULERS_DIR).rglob("*"))
        return {
            path.relative_to(project).as_posix(): (
                path.read_bytes(), stat.S_IMODE(path.stat().st_mode),
                *((path.stat().st_mtime_ns,) if times else ()),
            )
            for path in paths if path.is_file() and not any(
                part in {".transactions", ".plans", "__pycache__"} for part in path.parts
            )
        }

    def fail_activation(self, plan):
        with mock.patch.object(rule_maintenance, "prepare_domain_activation",
                               side_effect=RuntimeError("synthetic-second-stage-failure")):
            with self.assertRaisesRegex(Exception, "synthetic-second-stage-failure"):
                self.apply(plan)

    def crash_apply(self, project, plan, *, stage):
        """Kill a real writer after the selected transaction's State replacement."""
        (project / "crash-plan.json").write_text(json.dumps(plan))
        crash_script = """
import json
import os
import sys
from pathlib import Path
from rulers_lib import transactions
from rulers_lib.rule_maintenance import apply_rules_change

project, skill, crash_after = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
plan = json.loads((project / 'crash-plan.json').read_text())
original = transactions._atomic_replace_bytes
state_writes = 0
def crash_after_state_write(path, content, **kwargs):
    global state_writes
    result = original(path, content, **kwargs)
    if path.name == 'RULERS_STATE.json':
        state_writes += 1
        if state_writes == crash_after:
            os._exit(29)
    return result
transactions._atomic_replace_bytes = crash_after_state_write
apply_rules_change(plan=plan, skill_root=skill, reviewed_by=sys.argv[4], evidence=sys.argv[5])
"""
        crashed = subprocess.run(
            [sys.executable, "-c", crash_script, str(project), str(SKILL_ROOT), str(stage), REVIEWER, EVIDENCE],
            cwd=project, env={**os.environ, "PYTHONPATH": str(SKILL_ROOT / "scripts"), "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True,
        )
        self.assertEqual(29, crashed.returncode, crashed.stderr or crashed.stdout)

    def test_old_cli_remains_draft_and_replay_is_unchanged(self):
        project = self.fixture("backend", "security")
        candidate = self.candidate(project)
        security = copy.deepcopy(self.state(project)["domains"]["security"])
        self.cli_plan(project, candidate=candidate)
        self.cli(project, "rules-apply", "--plan", "rule-plan.json", *REVIEW)
        state = self.state(project)
        self.assertEqual((0, "draft"), (state["domains"]["backend"]["level"], state["domains"]["backend"]["review_status"]))
        self.assertEqual(security, state["domains"]["security"])
        before = self.snapshot(project, times=True)
        repeated = json.loads(self.cli(project, "rules-apply", "--plan", "rule-plan.json", *REVIEW).stdout)
        self.assertEqual([], repeated["changed_files"])
        self.assertEqual(before, self.snapshot(project, times=True))

    def test_legacy_content_only_adopts_when_target_and_dependency_are_healthy_drafts(self):
        project = self.fixture("backend", "security")
        state = self.state(project)
        state["domains"]["backend"]["requires_active"] = ["security"]
        for name in ("backend", "security"):
            state["domains"][name].update(level=0, review_status="draft", level3_ready=False,
                review={"reviewed_by": None, "reviewed_at": None, "evidence": None})
        self.save(project, state)
        dependency = copy.deepcopy(state["domains"]["security"])
        self.candidate(project)
        self.cli_plan(project)
        self.cli(project, "rules-apply", "--plan", "rule-plan.json", *REVIEW)
        state = self.state(project)
        self.assertEqual((0, "draft"), (state["domains"]["backend"]["level"], state["domains"]["backend"]["review_status"]))
        self.assertEqual(["security"], state["domains"]["backend"]["requires_active"])
        self.assertEqual(dependency, state["domains"]["security"])
        for path in (project / "rule-candidate").rglob("*.md"):
            self.assertEqual(path.read_bytes(), (self.target(project) / path.relative_to(project / "rule-candidate")).read_bytes())
        before = self.snapshot(project, times=True)
        repeated = json.loads(self.cli(project, "rules-apply", "--plan", "rule-plan.json", *REVIEW).stdout)
        self.assertEqual([], repeated["changed_files"])
        self.assertEqual(before, self.snapshot(project, times=True))

    def test_cli_one_approval_activates_only_target_and_degrades_real_dependents(self):
        project = self.fixture("backend", "security")
        state = self.state(project)
        state["domains"]["security"]["requires_active"] = ["backend"]
        self.save(project, state)
        self.candidate(project)
        self.cli_plan(project, activate=True)
        self.cli(project, "rules-apply", "--plan", "rule-plan.json", *REVIEW)
        state = self.state(project)
        self.assertEqual((2, "reviewed"), (state["domains"]["backend"]["level"], state["domains"]["backend"]["review_status"]))
        self.assertEqual(REVIEWER, state["domains"]["backend"]["review"]["reviewed_by"])
        self.assertEqual(EVIDENCE, state["domains"]["backend"]["review"]["evidence"])
        self.assertEqual((0, "draft"), (state["domains"]["security"]["level"], state["domains"]["security"]["review_status"]))
        self.assertEqual(["backend"], state["domains"]["security"]["requires_active"])
        self.assertEqual("complete", state["maintenance_execution"]["phase"])
        before = self.snapshot(project, times=True)
        repeated = json.loads(self.cli(project, "rules-apply", "--plan", "rule-plan.json", *REVIEW).stdout)
        self.assertEqual([], repeated["changed_files"])
        self.assertEqual(before, self.snapshot(project, times=True))

    def test_zero_difference_draft_can_be_explicitly_activated(self):
        project = self.fixture()
        self.candidate(project)
        self.apply(self.plan(project, activate=False))
        self.assertEqual("draft", self.state(project)["domains"]["backend"]["review_status"])
        plan = self.plan(project)
        self.assertEqual([], plan["added"] + plan["modified"] + plan["deleted"])
        before = {path.name: path.stat().st_mtime_ns for path in self.target(project).rglob("*.md")}
        self.apply(plan)
        self.assertEqual((2, "reviewed"), (self.state(project)["domains"]["backend"]["level"],
                                          self.state(project)["domains"]["backend"]["review_status"]))
        self.assertEqual(before, {path.name: path.stat().st_mtime_ns for path in self.target(project).rglob("*.md")})

    def test_readiness_only_preserves_body_review_dependencies_and_leaf_times(self):
        project = self.fixture("delivery", "backend")
        state = self.state(project)
        state["domains"]["backend"]["requires_active"] = ["delivery"]
        self.save(project, state)
        original_review = copy.deepcopy(state["domains"]["delivery"]["review"])
        original_dependent = copy.deepcopy(state["domains"]["backend"])
        self.candidate(project, "delivery", change=False)
        source = self.source(project)
        leaves = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in self.target(project, "delivery").rglob("*.md")}
        plan = self.plan(project, domain="delivery", source=source)
        self.apply(plan)
        state = self.state(project)
        review = copy.deepcopy(state["domains"]["delivery"]["review"])
        self.assertIn("readiness", review)
        declaration = review.pop("readiness")
        approval = review.pop("readiness_approval")
        self.assertEqual("readiness", approval["scope"])
        self.assertEqual(REVIEWER, approval["reviewed_by"])
        self.assertEqual(EVIDENCE, approval["evidence"])
        self.assertEqual(state["maintenance_execution"]["review"]["reviewed_at"], approval["reviewed_at"])
        self.assertEqual(plan["sha256"], approval["plan_sha256"])
        self.assertEqual(declaration["digest"], approval["declaration_digest"])
        self.assertEqual(original_review, review)
        self.assertEqual(original_dependent, state["domains"]["backend"])
        self.assertEqual(leaves, {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in self.target(project, "delivery").rglob("*.md")})
        inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
        self.assertTrue(evaluate_readiness(inspection, "delivery")["ready"])
        self.assertEqual(2, state["domains"]["delivery"]["level"])
        before = self.snapshot(project, times=True)
        self.assertEqual([], self.apply(plan)["changed_files"])
        self.assertEqual(before, self.snapshot(project, times=True))

    def test_readiness_source_requires_activation_and_cannot_supply_approval(self):
        project = self.fixture("delivery")
        self.candidate(project, "delivery", change=False)
        source = self.source(project)
        before = self.snapshot(project)
        with self.assertRaises(ValueError):
            self.plan(project, domain="delivery", activate=False, source=source)
        result = self.cli(project, "rules-plan", "--project-root", str(project), "--domain", "delivery",
                          "--candidate-dir", "rule-candidate", "--reason", "Synthetic invalid source",
                          "--readiness-source", source, "--output", "bad-plan.json", success=False)
        self.assertIn("activat", result.stderr.lower())
        valid = json.loads((project / source).read_text())
        for value in ({**valid, "reviewed_by": "forged-source-approval"},
                      {**valid, "security": ["../outside.md"]},
                      {**valid, "quality": [f"{RULERS_DIR}/delivery/NOT_ADOPTED.md"]}):
            with self.subTest(value=value):
                self.source(project, value=value)
                with self.assertRaises(ValueError):
                    self.plan(project, domain="delivery", source=source)
                self.assertEqual(before, self.snapshot(project))

    def test_source_candidate_and_state_changes_reject_previous_approval(self):
        project = self.fixture("delivery")
        self.candidate(project, "delivery")
        source = self.source(project)
        paths = (project / source, project / "rule-candidate/CI.md", self.state_path(project))
        for path in paths:
            with self.subTest(path=path.name):
                plan = self.plan(project, domain="delivery", source=source)
                original = path.read_bytes()
                if path == self.state_path(project):
                    state = self.state(project)
                    state["last_operation"]["test_concurrent_change"] = True
                    self.save(project, state)
                else:
                    path.write_bytes(original + b"\n ")
                before = self.snapshot(project)
                with self.assertRaises(ValueError):
                    self.apply(plan)
                self.assertEqual(before, self.snapshot(project))
                path.write_bytes(original)

    def test_skill_inputs_are_bound_without_editing_development_skill(self):
        project = self.fixture()
        self.candidate(project)
        skill_copy = project / "isolated-skill"
        shutil.copytree(SKILL_ROOT, skill_copy, ignore=shutil.ignore_patterns("__pycache__"))
        plan = self.plan(project, skill_root=skill_copy)
        skill_entry = skill_copy / "SKILL.md"
        skill_entry.write_text(skill_entry.read_text() + "\nSynthetic changed workflow input.\n")
        before = self.snapshot(project)
        with self.assertRaises(ValueError):
            self.apply(plan, skill_root=skill_copy)
        self.assertEqual(before, self.snapshot(project))

    def test_first_stage_exception_rolls_back_content_state_and_permissions(self):
        project = self.fixture()
        self.candidate(project)
        leaf = next(path for path in self.target(project).rglob("*.md") if path.name != "INDEX.md")
        leaf.chmod(0o640)
        plan = self.plan(project)
        before = self.snapshot(project)
        with mock.patch.object(rule_maintenance, "scoped_validation_issues",
                               side_effect=RuntimeError("synthetic-first-stage-failure")):
            with self.assertRaisesRegex(Exception, "synthetic-first-stage-failure"):
                self.apply(plan)
        self.assertEqual(before, self.snapshot(project))

    def test_second_stage_exception_preserves_draft_and_same_approval_resumes(self):
        project = self.fixture()
        self.candidate(project)
        plan = self.plan(project)
        self.fail_activation(plan)
        state = self.state(project)
        self.assertEqual((0, "draft"), (state["domains"]["backend"]["level"], state["domains"]["backend"]["review_status"]))
        self.assertEqual("activation_pending", state["maintenance_execution"]["phase"])
        for path in (project / "rule-candidate").rglob("*.md"):
            self.assertEqual(path.read_bytes(), (self.target(project) / path.relative_to(project / "rule-candidate")).read_bytes())
        leaf_times = {str(path): path.stat().st_mtime_ns for path in self.target(project).rglob("*.md")}
        before = self.snapshot(project)
        with self.assertRaises(ValueError):
            self.apply(plan, reviewer="different-synthetic-reviewer")
        with self.assertRaises(ValueError):
            self.apply(plan, evidence="different-synthetic-approval")
        self.assertEqual(before, self.snapshot(project))
        self.apply(plan)
        self.assertEqual(2, self.state(project)["domains"]["backend"]["level"])
        self.assertEqual("complete", self.state(project)["maintenance_execution"]["phase"])
        self.assertEqual(leaf_times, {str(path): path.stat().st_mtime_ns for path in self.target(project).rglob("*.md")})
        before = self.snapshot(project, times=True)
        self.assertEqual([], self.apply(plan)["changed_files"])
        self.assertEqual(before, self.snapshot(project, times=True))

    def test_failed_readiness_only_update_keeps_existing_body_trust(self):
        project = self.fixture("delivery", "backend")
        state = self.state(project)
        state["domains"]["backend"]["requires_active"] = ["delivery"]
        self.save(project, state)
        self.candidate(project, "delivery", change=False)
        plan = self.plan(project, domain="delivery", source=self.source(project))
        original_domains = copy.deepcopy(state["domains"])
        self.fail_activation(plan)
        self.assertEqual(original_domains, self.state(project)["domains"])
        inspection = inspect_project(project_root=project, rulers_dir=RULERS_DIR)
        self.assertNotIn("delivery", inspection.invalid_domains)
        self.assertNotIn("backend", inspection.invalid_domains)

    def test_changes_between_stages_cannot_be_granted_original_approval(self):
        for changed in ("target", "candidate", "state", "dependency"):
            with self.subTest(changed=changed):
                project = self.fixture("backend", "security")
                self.candidate(project)
                plan = self.plan(project)
                self.fail_activation(plan)
                if changed == "target":
                    path = self.target(project) / "ARCHITECTURE.md"
                    path.write_text(path.read_text() + "\nUnreviewed concurrent output change.\n")
                elif changed == "candidate":
                    path = project / "rule-candidate/ARCHITECTURE.md"
                    path.write_text(path.read_text() + "\nUnreviewed concurrent candidate change.\n")
                else:
                    state = self.state(project)
                    if changed == "dependency":
                        state["domains"]["backend"]["requires_active"] = ["security"]
                    else:
                        state["test_concurrent_change"] = True
                    self.save(project, state)
                before = self.snapshot(project)
                with self.assertRaises(ValueError):
                    self.apply(plan)
                self.assertEqual(before, self.snapshot(project))

    def test_pending_replacement_is_explicit_in_a_new_reviewed_plan(self):
        project = self.fixture()
        self.candidate(project)
        old_plan = self.plan(project)
        self.fail_activation(old_plan)
        pending = copy.deepcopy(self.state(project)["maintenance_execution"])
        self.candidate(project, name="replacement-candidate")
        new_plan = self.plan(project, candidate="replacement-candidate")
        self.assertIn("supersedes", new_plan)
        self.assertIn(old_plan["sha256"], json.dumps(new_plan["supersedes"]))
        self.assertEqual(pending["applied_files"], new_plan["supersedes"]["applied_files"])
        self.assertEqual(pending["output_sha256"], new_plan["supersedes"]["output_sha256"])
        self.assertEqual(["backend"], new_plan["supersedes"]["remaining_draft_domains"])
        self.apply(new_plan, reviewer="synthetic-replacement-auditor", evidence="test-only-explicit-replacement-approval")
        state = self.state(project)
        self.assertEqual((2, "reviewed"), (state["domains"]["backend"]["level"], state["domains"]["backend"]["review_status"]))
        self.assertEqual("synthetic-replacement-auditor", state["domains"]["backend"]["review"]["reviewed_by"])
        before = self.snapshot(project)
        with self.assertRaises(ValueError):
            self.apply(old_plan)
        self.assertEqual(before, self.snapshot(project))

    def test_unrelated_bad_domain_is_diagnostic_but_actual_bad_dependency_blocks(self):
        for dependent in (False, True):
            with self.subTest(dependent=dependent):
                project = self.fixture("backend", "security")
                if dependent:
                    state = self.state(project)
                    state["domains"]["backend"]["requires_active"] = ["security"]
                    self.save(project, state)
                path = self.target(project, "security") / "SECRETS.md"
                path.write_text(path.read_text() + "\nUnreviewed security drift.\n")
                self.candidate(project)
                before = self.snapshot(project)
                if dependent:
                    with self.assertRaises(ValueError):
                        self.apply(self.plan(project))
                    self.assertEqual(before, self.snapshot(project))
                else:
                    self.apply(self.plan(project))
                    self.assertEqual(2, self.state(project)["domains"]["backend"]["level"])
                    context = json.loads(self.cli(project, "--mode", "context", "--project-root", str(project),
                                                  "--domain", "backend", script="validate_rulers.py").stdout)
                    self.assertFalse(context["blocked"])
                    self.assertIn("backend", context["routes"])
                    self.cli(project, "--mode", "runtime", "--project-root", str(project),
                             script="validate_rulers.py", success=False)

    def test_plan_tampering_or_apply_time_flags_cannot_expand_approved_activation(self):
        project = self.fixture("backend", "security")
        self.candidate(project)
        plan = self.plan(project, activate=False)
        altered = copy.deepcopy(plan)
        altered["activate_on_apply"] = True
        before = self.snapshot(project)
        with self.assertRaises(ValueError):
            self.apply(altered)
        (project / "rule-plan.json").write_text(json.dumps(plan))
        self.cli(project, "rules-apply", "--plan", "rule-plan.json", *REVIEW,
                 "--activate-on-apply", success=False)
        self.assertEqual(before, self.snapshot(project))

    def test_process_interruption_restores_only_same_plan_and_resumes(self):
        for stage in (1, 2):
            with self.subTest(stage=stage):
                project = self.fixture()
                self.candidate(project)
                plan = self.plan(project)
                self.crash_apply(project, plan, stage=stage)
                self.apply(plan)
                state = self.state(project)
                self.assertEqual("complete", state["maintenance_execution"]["phase"])
                self.assertEqual((2, "reviewed"), (state["domains"]["backend"]["level"], state["domains"]["backend"]["review_status"]))
                before = self.snapshot(project, times=True)
                self.assertEqual([], self.apply(plan)["changed_files"])
                self.assertEqual(before, self.snapshot(project, times=True))

    def test_recomputed_output_digest_cannot_authorize_modified_state(self):
        for phase in ("activation_pending", "complete"):
            with self.subTest(phase=phase):
                project = self.fixture()
                self.candidate(project)
                plan = self.plan(project)
                if phase == "activation_pending":
                    self.fail_activation(plan)
                else:
                    self.apply(plan)
                state = self.state(project)
                self.assertEqual(phase, state["maintenance_execution"]["phase"])
                state["unapproved_state_change"] = "synthetic-forged-recovery-input"
                # The attacker updates its own recovery claim to match the changed State.
                state["maintenance_execution"]["output_sha256"] = rule_maintenance._state_identity(state)
                self.save(project, state)
                before = self.snapshot(project)
                with self.assertRaises(ValueError):
                    self.apply(plan)
                self.assertEqual(before, self.snapshot(project))

    def test_self_consistent_forged_leaf_snapshot_cannot_replace_approved_original(self):
        project = self.fixture()
        self.candidate(project)
        plan = self.plan(project)
        self.crash_apply(project, plan, stage=1)
        layout = resolve_layout(project, RULERS_DIR)
        interrupted = inspect_incomplete_transaction(layout)
        self.assertIsNotNone(interrupted)
        action = next(action for action in interrupted.actions
                      if action.path != f"{RULERS_DIR}/RULERS_STATE.json" and action.original_existed)
        transaction_root = layout.transaction_root(interrupted.transaction_id)
        snapshot = transaction_root / action.snapshot_ref
        snapshot.write_bytes(snapshot.read_bytes() + b"\nSynthetic forged original rule content.\n")
        forged_hash = file_sha256(snapshot)
        journal_path = transaction_root / "journal.json"
        journal = json.loads(journal_path.read_text())
        entry = next(entry for entry in journal["actions"] if entry["path"] == action.path)
        entry["original_sha256"] = forged_hash
        entry["snapshot_sha256"] = forged_hash
        journal_path.write_text(json.dumps(journal))
        # The generic journal checks still pass: only the approved plan reveals the forgery.
        self.assertIsNotNone(inspect_incomplete_transaction(layout))
        before = self.snapshot(project)
        with self.assertRaises(ValueError):
            self.apply(plan)
        self.assertEqual(before, self.snapshot(project))

    def test_unrelated_interrupted_transaction_is_not_automatically_recovered(self):
        project = self.fixture()
        self.candidate(project)
        plan = self.plan(project)
        crash_script = """
import os
import sys
from pathlib import Path
from rulers_lib.paths import resolve_layout
from rulers_lib.transactions import file_transaction

layout = resolve_layout(Path(sys.argv[1]), 'documents/rulers')
with file_transaction(layout=layout, plan_id='synthetic-unrelated-transaction') as transaction:
    transaction.replace_bytes(Path('documents/rulers/core/WORKFLOW.md'), b'Unrelated interrupted write\\n')
    os._exit(29)
"""
        crashed = subprocess.run(
            [sys.executable, "-c", crash_script, str(project)], cwd=project,
            env={**os.environ, "PYTHONPATH": str(SKILL_ROOT / "scripts"), "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True,
        )
        self.assertEqual(29, crashed.returncode, crashed.stderr or crashed.stdout)
        before = self.snapshot(project)
        with self.assertRaises((ValueError, RuntimeError)):
            self.apply(plan)
        self.assertEqual(before, self.snapshot(project))


if __name__ == "__main__":
    unittest.main()
