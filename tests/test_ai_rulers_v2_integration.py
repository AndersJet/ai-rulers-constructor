from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-rulers-init"
CLI = SKILL_ROOT / "scripts" / "rulers_init.py"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_rulers.py"


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )


def candidate_rule(title: str) -> str:
    return f"""# {title}

```yaml
metadata:
  applies_to:
    - \"**/*\"
  trigger_keywords:
    - project-specific
  must_load_with:
    - documents/rulers/AGENTS.md
```

Project-specific reviewed candidate.
"""


class FreshInitializationIntegrationTest(unittest.TestCase):
    def test_fresh_apply_creates_only_runtime_assets_and_preserves_root_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "AGENTS.md").write_text(
                "# Team instructions\n\nKeep this content.\n",
                encoding="utf-8",
            )
            plan_path = project / "rulers-plan.json"

            plan = run_cli(
                "plan",
                "--project-root",
                str(project),
                "--rulers-dir",
                "documents/coding-standards",
                "--policy",
                "project-native",
                "--output",
                str(plan_path),
                cwd=ROOT,
            )
            self.assertEqual(0, plan.returncode, plan.stderr)

            apply_result = run_cli(
                "apply",
                "--plan",
                str(plan_path),
                cwd=ROOT,
            )
            self.assertEqual(0, apply_result.returncode, apply_result.stderr)

            rulers = project / "documents" / "coding-standards"
            state = json.loads((rulers / "RULERS_STATE.json").read_text(encoding="utf-8"))
            root_agents = (project / "AGENTS.md").read_text(encoding="utf-8")

            self.assertEqual("profile_draft", state["phase"])
            self.assertEqual(0, state["domains"]["core"]["level"])
            self.assertIn("Keep this content.", root_agents)
            self.assertIn("ai-rulers-init:begin", root_agents)
            self.assertFalse((rulers / "bootstrap").exists())
            self.assertFalse((rulers / "PROJECT_PROFILE.template.md").exists())
            self.assertFalse((rulers / "CHANGELOG.template.md").exists())
            self.assertFalse((project / "CHANGELOG.md").exists())

            candidate = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "candidate",
                    "--project-root",
                    str(project),
                    "--rulers-dir",
                    "documents/coding-standards",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, candidate.returncode, candidate.stdout + candidate.stderr)

    def test_reapplying_same_plan_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            plan = run_cli(
                "plan",
                "--project-root",
                str(project),
                "--output",
                str(plan_path),
                cwd=ROOT,
            )
            self.assertEqual(0, plan.returncode, plan.stderr)

            first = run_cli("apply", "--plan", str(plan_path), cwd=ROOT)
            second = run_cli("apply", "--plan", str(plan_path), cwd=ROOT)

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            summary = json.loads(second.stdout)
            self.assertEqual([], summary["changed_files"])

    def test_reapply_refuses_to_overwrite_drifted_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            hard_constraints = project / "documents" / "rulers" / "core" / "HARD_CONSTRAINTS.md"
            manual_text = hard_constraints.read_text(encoding="utf-8") + "\nmanual ownership change\n"
            hard_constraints.write_text(manual_text, encoding="utf-8")

            reapplied = run_cli("apply", "--plan", str(plan_path), cwd=ROOT)

            self.assertNotEqual(0, reapplied.returncode)
            self.assertIn("VR040", reapplied.stderr)
            self.assertEqual(manual_text, hard_constraints.read_text(encoding="utf-8"))

    def test_status_and_resume_use_recorded_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)

            status = run_cli("status", "--project-root", str(project), cwd=ROOT)
            resume = run_cli("resume", "--project-root", str(project), cwd=ROOT)

            self.assertEqual(0, status.returncode, status.stderr)
            self.assertEqual("profile_draft", json.loads(status.stdout)["phase"])
            self.assertEqual(0, resume.returncode, resume.stderr)
            self.assertEqual("review-profile", json.loads(resume.stdout)["next_action"])

    def test_apply_refuses_to_overwrite_unmanaged_runtime_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            conflict = project / "documents" / "rulers" / "core" / "HARD_CONSTRAINTS.md"
            conflict.parent.mkdir(parents=True)
            conflict.write_text("human-owned constraints\n", encoding="utf-8")
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )

            applied = run_cli("apply", "--plan", str(plan_path), cwd=ROOT)

            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertIn(
                "documents/rulers/core/HARD_CONSTRAINTS.md",
                [item["path"] for item in plan["preconditions"]["write_set"] if item["sha256"]],
            )
            self.assertNotEqual(0, applied.returncode)
            self.assertIn("VR041", applied.stderr)
            self.assertEqual("human-owned constraints\n", conflict.read_text(encoding="utf-8"))

    def test_profile_can_be_edited_reviewed_and_reapplied_without_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            profile = project / "documents" / "rulers" / "PROJECT_PROFILE.md"
            reviewed_content = profile.read_text(encoding="utf-8") + "\nObserved runtime: Python 3.14\n"
            profile.write_text(reviewed_content, encoding="utf-8")

            review = run_cli(
                "review-profile",
                "--project-root",
                str(project),
                "--reviewed-by",
                "owner",
                "--evidence",
                "profile-reviewed",
                cwd=ROOT,
            )
            reapplied = run_cli("apply", "--plan", str(plan_path), cwd=ROOT)

            self.assertEqual(0, review.returncode, review.stderr)
            self.assertNotEqual(0, reapplied.returncode)  # State changed: the old plan is stale.
            next_plan = project / "after-review.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--output", str(next_plan), cwd=ROOT).returncode)
            resumed = run_cli("apply", "--plan", str(next_plan), cwd=ROOT)
            self.assertEqual(0, resumed.returncode, resumed.stderr)
            self.assertEqual(reviewed_content, profile.read_text(encoding="utf-8"))

    def test_candidate_validation_reports_missing_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            managed = project / "documents" / "rulers" / "scripts" / "rulers_lib" / "issues.py"
            managed.unlink()

            candidate = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "candidate",
                    "--project-root",
                    str(project),
                    "--rulers-dir",
                    "documents/rulers",
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(0, candidate.returncode)
            codes = {issue["code"] for issue in json.loads(candidate.stdout)["issues"]}
            self.assertIn("VR040", codes)

    def test_resume_plan_preserves_recorded_policy_and_rejects_implicit_switch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            initial_plan = project / "initial-plan.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--policy", "project-native", "--output", str(initial_plan), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("apply", "--plan", str(initial_plan), cwd=ROOT).returncode)
            resume_plan = project / "resume-plan.json"

            resumed = run_cli("plan", "--project-root", str(project), "--output", str(resume_plan), cwd=ROOT)
            switched = run_cli("plan", "--project-root", str(project), "--policy", "strict-cn", cwd=ROOT)

            self.assertEqual(0, resumed.returncode, resumed.stderr)
            self.assertEqual("project-native", json.loads(resume_plan.read_text(encoding="utf-8"))["preconditions"]["policy"]["id"])
            self.assertNotEqual(0, switched.returncode)
            self.assertIn("policy", switched.stderr.lower())

    def test_status_reports_repair_when_managed_files_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--output", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            (project / "documents" / "rulers" / "scripts" / "rulers_lib" / "issues.py").unlink()

            status = run_cli("status", "--project-root", str(project), cwd=ROOT)

            self.assertEqual(0, status.returncode, status.stderr)
            payload = json.loads(status.stdout)
            self.assertEqual("repair_required", payload["phase"])
            self.assertEqual("repair", payload["next_action"])
            self.assertIn("VR040", payload["issues"])


class DomainActivationIntegrationTest(unittest.TestCase):
    def test_security_and_delivery_activation_records_level3_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "security").mkdir()
            (project / ".github" / "workflows").mkdir(parents=True)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(
                0,
                run_cli(
                    "review-profile",
                    "--project-root",
                    str(project),
                    "--reviewed-by",
                    "owner",
                    "--evidence",
                    "profile-approved",
                    cwd=ROOT,
                ).returncode,
            )

            for domain in ("security", "delivery"):
                rendered = run_cli(
                    "render-domain-candidate",
                    "--project-root",
                    str(project),
                    "--domain",
                    domain,
                    cwd=ROOT,
                )
                self.assertEqual(0, rendered.returncode, rendered.stderr)
                activated = run_cli(
                    "activate-domain",
                    "--project-root",
                    str(project),
                    "--domain",
                    domain,
                    "--reviewed-by",
                    "security-owner" if domain == "security" else "release-owner",
                    "--evidence",
                    f"{domain}-approved",
                    cwd=ROOT,
                )
                self.assertEqual(0, activated.returncode, activated.stderr)

            state = json.loads(
                (project / "documents" / "rulers" / "RULERS_STATE.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(2, state["domains"]["security"]["level"])
            self.assertEqual(2, state["domains"]["delivery"]["level"])
            self.assertTrue(state["domains"]["delivery"]["level3_ready"])
            self.assertTrue(
                (project / "documents" / "rulers" / "security" / "INDEX.md").is_file()
            )
            self.assertTrue(
                (project / "documents" / "rulers" / "delivery" / "ROLLBACK.md").is_file()
            )
            self.assertFalse((project / "documents" / "rulers" / "domains").exists())

    def test_delivery_cannot_activate_before_security_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / ".github" / "workflows").mkdir(parents=True)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(
                0,
                run_cli(
                    "review-profile",
                    "--project-root",
                    str(project),
                    "--reviewed-by",
                    "owner",
                    "--evidence",
                    "profile-approved",
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "render-domain-candidate",
                    "--project-root",
                    str(project),
                    "--domain",
                    "delivery",
                    cwd=ROOT,
                ).returncode,
            )

            activated = run_cli(
                "activate-domain",
                "--project-root",
                str(project),
                "--domain",
                "delivery",
                "--reviewed-by",
                "release-owner",
                "--evidence",
                "delivery-approved",
                cwd=ROOT,
            )

            self.assertNotEqual(0, activated.returncode)
            self.assertIn("security", activated.stderr)

    def test_runtime_validation_rejects_missing_active_domain_leaf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "security").mkdir()
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(
                0,
                run_cli(
                    "review-profile",
                    "--project-root",
                    str(project),
                    "--reviewed-by",
                    "owner",
                    "--evidence",
                    "profile-approved",
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "render-domain-candidate",
                    "--project-root",
                    str(project),
                    "--domain",
                    "security",
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli(
                    "activate-domain",
                    "--project-root",
                    str(project),
                    "--domain",
                    "security",
                    "--reviewed-by",
                    "security-owner",
                    "--evidence",
                    "security-approved",
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli("mark-runtime-ready", "--project-root", str(project), cwd=ROOT).returncode,
            )
            missing = project / "documents" / "rulers" / "security" / "SECRETS.md"
            missing.unlink()

            runtime = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "runtime",
                    "--project-root",
                    str(project),
                    "--rulers-dir",
                    "documents/rulers",
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(0, runtime.returncode)
            codes = {issue["code"] for issue in json.loads(runtime.stdout)["issues"]}
            self.assertIn("VR050", codes)

    def test_domain_render_refuses_unmanaged_target_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--output", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("review-profile", "--project-root", str(project), "--reviewed-by", "owner", "--evidence", "approved", cwd=ROOT).returncode)
            conflict = project / "documents" / "rulers" / "security" / "INDEX.md"
            conflict.parent.mkdir(parents=True)
            conflict.write_text("human security rules\n", encoding="utf-8")

            rendered = run_cli("render-domain-candidate", "--project-root", str(project), "--domain", "security", cwd=ROOT)

            self.assertNotEqual(0, rendered.returncode)
            self.assertIn("VR041", rendered.stderr)
            self.assertEqual("human security rules\n", conflict.read_text(encoding="utf-8"))

    def test_domain_rerender_refuses_managed_file_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--output", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("review-profile", "--project-root", str(project), "--reviewed-by", "owner", "--evidence", "approved", cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("render-domain-candidate", "--project-root", str(project), "--domain", "security", cwd=ROOT).returncode)
            secrets = project / "documents" / "rulers" / "security" / "SECRETS.md"
            drifted = secrets.read_text(encoding="utf-8") + "\nmanual security change\n"
            secrets.write_text(drifted, encoding="utf-8")

            rendered = run_cli("render-domain-candidate", "--project-root", str(project), "--domain", "security", cwd=ROOT)

            self.assertNotEqual(0, rendered.returncode)
            self.assertIn("VR040", rendered.stderr)
            self.assertEqual(drifted, secrets.read_text(encoding="utf-8"))

    def test_project_generated_domain_can_be_registered_and_activated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "server").mkdir()
            plan_path = project / "rulers-plan.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--output", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("review-profile", "--project-root", str(project), "--reviewed-by", "owner", "--evidence", "approved", cwd=ROOT).returncode)
            backend = project / "documents" / "rulers" / "backend"
            backend.mkdir(parents=True)
            for name in ("INDEX.md", "ARCHITECTURE.md", "API_SECURITY.md", "TESTING.md", "DATA_ACCESS.md", "CONFIGURATION.md", "OBSERVABILITY.md"):
                (backend / name).write_text(candidate_rule(name), encoding="utf-8")
            index = backend / "INDEX.md"
            index.write_text(index.read_text() + "\n" + "\n".join(
                f"[{path.name}]({path.name})" for path in backend.glob("*.md") if path.name != "INDEX.md"
            ), encoding="utf-8")

            registered = run_cli("register-domain-candidate", "--project-root", str(project), "--domain", "backend", cwd=ROOT)
            activated = run_cli("activate-domain", "--project-root", str(project), "--domain", "backend", "--reviewed-by", "backend-owner", "--evidence", "backend-approved", cwd=ROOT)

            self.assertEqual(0, registered.returncode, registered.stderr)
            self.assertEqual(0, activated.returncode, activated.stderr)
            state = json.loads((project / "documents" / "rulers" / "RULERS_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual(2, state["domains"]["backend"]["level"])

    def test_project_generated_domain_rejects_incomplete_rule_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "server").mkdir()
            plan_path = project / "rulers-plan.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--output", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("review-profile", "--project-root", str(project), "--reviewed-by", "owner", "--evidence", "approved", cwd=ROOT).returncode)
            backend = project / "documents" / "rulers" / "backend"
            backend.mkdir(parents=True)
            for name in ("INDEX.md", "ARCHITECTURE.md", "API_SECURITY.md", "TESTING.md", "DATA_ACCESS.md", "CONFIGURATION.md", "OBSERVABILITY.md"):
                content = "# Missing metadata\n" if name == "API_SECURITY.md" else candidate_rule(name)
                (backend / name).write_text(content, encoding="utf-8")

            registered = run_cli("register-domain-candidate", "--project-root", str(project), "--domain", "backend", cwd=ROOT)

            self.assertNotEqual(0, registered.returncode)
            self.assertIn("VR106", registered.stderr)


class ValidationLifecycleIntegrationTest(unittest.TestCase):
    def test_runtime_validation_rejects_unreviewed_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(
                0,
                run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode,
            )

            runtime = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "runtime",
                    "--project-root",
                    str(project),
                    "--rulers-dir",
                    "documents/rulers",
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(0, runtime.returncode)
            codes = {issue["code"] for issue in json.loads(runtime.stdout)["issues"]}
            self.assertIn("VR012", codes)

    def test_reviewed_profile_can_reach_runtime_ready_and_pass_runtime_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)

            review = run_cli(
                "review-profile",
                "--project-root",
                str(project),
                "--reviewed-by",
                "project-owner",
                "--evidence",
                "approved-in-review",
                cwd=ROOT,
            )
            self.assertEqual(0, review.returncode, review.stderr)

            ready = run_cli(
                "mark-runtime-ready",
                "--project-root",
                str(project),
                cwd=ROOT,
            )
            self.assertEqual(0, ready.returncode, ready.stderr)

            runtime = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "runtime",
                    "--project-root",
                    str(project),
                    "--rulers-dir",
                    "documents/rulers",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, runtime.returncode, runtime.stdout + runtime.stderr)

    def test_candidate_validation_reports_managed_file_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(
                0,
                run_cli(
                    "plan",
                    "--project-root",
                    str(project),
                    "--output",
                    str(plan_path),
                    cwd=ROOT,
                ).returncode,
            )
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            hard_constraints = project / "documents" / "rulers" / "core" / "HARD_CONSTRAINTS.md"
            hard_constraints.write_text(
                hard_constraints.read_text(encoding="utf-8") + "\nmanual drift\n",
                encoding="utf-8",
            )

            candidate = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "candidate",
                    "--project-root",
                    str(project),
                    "--rulers-dir",
                    "documents/rulers",
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(0, candidate.returncode)
            codes = {issue["code"] for issue in json.loads(candidate.stdout)["issues"]}
            self.assertIn("VR040", codes)

    def test_runtime_ready_transition_rejects_invalid_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            plan_path = project / "rulers-plan.json"
            self.assertEqual(0, run_cli("plan", "--project-root", str(project), "--output", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("apply", "--plan", str(plan_path), cwd=ROOT).returncode)
            self.assertEqual(0, run_cli("review-profile", "--project-root", str(project), "--reviewed-by", "owner", "--evidence", "approved", cwd=ROOT).returncode)
            validator = project / "documents" / "rulers" / "scripts" / "validate_rulers.py"
            validator.unlink()

            ready = run_cli("mark-runtime-ready", "--project-root", str(project), cwd=ROOT)

            self.assertNotEqual(0, ready.returncode)
            self.assertIn("VR040", ready.stderr)
            state = json.loads((project / "documents" / "rulers" / "RULERS_STATE.json").read_text(encoding="utf-8"))
            self.assertNotEqual("runtime_ready", state["phase"])


class LegacyMigrationIntegrationTest(unittest.TestCase):
    def test_legacy_profile_without_review_becomes_review_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            rulers = project / "documents" / "rulers"
            rulers.mkdir(parents=True)
            (rulers / "PROJECT_PROFILE.md").write_text(
                "# Project profile\n\n| Core | Level 1 | | |\n",
                encoding="utf-8",
            )

            result = run_cli(
                "migrate-v1",
                "--project-root",
                str(project),
                "--apply",
                cwd=ROOT,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            state = json.loads((rulers / "RULERS_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual("profile_draft", state["phase"])
            self.assertEqual("draft", state["profile"]["status"])
            self.assertEqual(0, state["domains"]["core"]["level"])

    def test_legacy_migration_preserves_existing_root_agents_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "AGENTS.md").write_text(
                "# Human rules\n\nNever delete this paragraph.\n",
                encoding="utf-8",
            )
            rulers = project / "documents" / "rulers"
            rulers.mkdir(parents=True)
            (rulers / "PROJECT_PROFILE.md").write_text("# Legacy profile\n", encoding="utf-8")

            result = run_cli(
                "migrate-v1",
                "--project-root",
                str(project),
                "--apply",
                cwd=ROOT,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            root_agents = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Never delete this paragraph.", root_agents)
            self.assertEqual(1, root_agents.count("ai-rulers-init:begin"))

    def test_legacy_migration_tracks_managed_assets_and_preserves_profile_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            rulers = project / "documents" / "rulers"
            rulers.mkdir(parents=True)
            legacy_profile = "# Legacy profile\n\nKeep these discovered facts.\n"
            (rulers / "PROJECT_PROFILE.md").write_text(legacy_profile, encoding="utf-8")

            migrated = run_cli("migrate-v1", "--project-root", str(project), "--apply", cwd=ROOT)
            plan_path = project / "resume-plan.json"
            planned = run_cli("plan", "--project-root", str(project), "--output", str(plan_path), cwd=ROOT)
            resumed = run_cli("apply", "--plan", str(plan_path), cwd=ROOT)

            self.assertEqual(0, migrated.returncode, migrated.stderr)
            self.assertEqual(0, planned.returncode, planned.stderr)
            self.assertEqual(0, resumed.returncode, resumed.stderr)
            state = json.loads((rulers / "RULERS_STATE.json").read_text(encoding="utf-8"))
            hard_constraints = "documents/rulers/core/HARD_CONSTRAINTS.md"
            profile = "documents/rulers/PROJECT_PROFILE.md"
            self.assertEqual("managed", state["managed_files"][hard_constraints]["ownership"])
            self.assertEqual("collaborative", state["managed_files"][profile]["ownership"])
            self.assertEqual(legacy_profile, (rulers / "PROJECT_PROFILE.md").read_text(encoding="utf-8"))

    def test_legacy_migration_supports_project_native_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            rulers = project / "documents" / "rulers"
            rulers.mkdir(parents=True)
            (rulers / "PROJECT_PROFILE.md").write_text("# Legacy profile\n", encoding="utf-8")

            migrated = run_cli(
                "migrate-v1",
                "--project-root",
                str(project),
                "--policy",
                "project-native",
                "--apply",
                cwd=ROOT,
            )

            self.assertEqual(0, migrated.returncode, migrated.stderr)
            state = json.loads((rulers / "RULERS_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual("project-native", state["policy"]["id"])
            self.assertFalse((project / "CHANGELOG.md").exists())


if __name__ == "__main__":
    unittest.main()
