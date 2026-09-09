from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-rulers-init"
PACKAGE = ROOT / "skills" / "ai-rulers-init.skill"


class UnifiedLifecycleDocumentationTest(unittest.TestCase):
    def test_readmes_document_state_modes_policies_and_migration(self) -> None:
        for filename in ("README.md", "README-zh.md"):
            with self.subTest(filename=filename):
                text = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn("RULERS_STATE.json", text)
                self.assertIn("--mode candidate", text)
                self.assertIn("project-native", text)
                self.assertIn("migrate-v1", text)
                self.assertIn("register-domain-candidate", text)
                self.assertIn("collaborative", text)

    def test_contributing_uses_v2_validator_and_packaging_checks(self) -> None:
        for filename in ("CONTRIBUTING.md", "CONTRIBUTING-zh.md"):
            with self.subTest(filename=filename):
                text = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn("--mode template", text)
                self.assertIn("test_package_parity", text)

    def test_governance_declares_state_and_profile_ownership(self) -> None:
        governance = (
            SKILL_ROOT / "templates" / "runtime" / "core" / "DOC_GOVERNANCE.md"
        ).read_text(encoding="utf-8")
        maintenance = (
            SKILL_ROOT / "templates" / "runtime" / "core" / "RULER_MAINTENANCE.md"
        ).read_text(encoding="utf-8")

        self.assertIn("State 保存生命周期、审阅与文件所有权", governance)
        self.assertIn("Profile 保存 observed 事实与 approved 决定", governance)
        self.assertIn("rules-plan/rules-apply", maintenance)

    def test_changelog_records_v2_lifecycle_change(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("RULERS_STATE.json", changelog)
        self.assertIn("三阶段校验", changelog)
        self.assertIn("VR041", changelog)


class ReproduciblePackageTest(unittest.TestCase):
    def test_two_builds_are_byte_identical(self) -> None:
        from scripts.package_skill import build_skill_package

        with tempfile.TemporaryDirectory() as td:
            out1 = Path(td) / "a.skill"
            out2 = Path(td) / "b.skill"
            build_skill_package(SKILL_ROOT, out1)
            build_skill_package(SKILL_ROOT, out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())

    def test_members_are_safe_sorted_single_root_and_exclude_dev_assets(self) -> None:
        with ZipFile(PACKAGE) as archive:
            names = archive.namelist()
        self.assertTrue(all(n.startswith("ai-rulers-init/") for n in names))
        self.assertEqual(names, sorted(names))
        self.assertNotIn("ai-rulers-init/evals/", names)
        for name in names:
            self.assertNotIn("..", name)
            self.assertFalse(name.startswith("/"))
            self.assertNotIn(".DS_Store", name)
            self.assertNotIn("__pycache__", name)

    def test_cli_validates_template_and_writes_requested_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "test.skill"
            result = subprocess.run(
                [sys.executable, "-m", "scripts.package_skill",
                 "--skill-root", str(SKILL_ROOT), "--output", str(out)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)


class ContextBudgetReportTest(unittest.TestCase):
    def test_json_schema_and_hard_limits(self) -> None:
        from scripts.report_context_budget import measure_context_budget

        report = measure_context_budget(
            rulers_dir="documents/rulers",
            domains=["backend"], include_token_trend=False,
        )
        for key in ("limits", "measurements", "load_graph", "growth", "tokenizer", "checks", "all_pass"):
            self.assertIn(key, report)
        self.assertIn("skill_lines", report["limits"])
        self.assertIn("context_bytes", report["limits"])
        self.assertTrue(report["all_pass"])

    def test_load_graph_excludes_state_runtime_index_references_and_siblings(self) -> None:
        from scripts.report_context_budget import measure_context_budget

        report = measure_context_budget(
            rulers_dir="documents/rulers",
            domains=["backend"], include_token_trend=False,
        )
        lg = report["load_graph"]
        self.assertEqual("isolated-synthetic-runtime", report["measurement_source"])
        self.assertEqual(["documents/rulers/backend/INDEX.md"], lg["domain_indexes"])
        all_paths = lg["core"] + lg["domain_indexes"]
        if lg["profile"]:
            all_paths = all_paths + [lg["profile"]]
        for p in all_paths:
            self.assertNotIn("RULERS_STATE.json", p)
        # Only selected domain indexes should appear
        for idx in lg["domain_indexes"]:
            self.assertIn("backend", idx)
        # Sibling domains must not appear
        all_str = str(lg["domain_indexes"])
        self.assertNotIn("database", all_str)
        self.assertNotIn("frontend", all_str)

    def test_managed_one_to_hundred_and_reconcile_zero_to_twenty_do_not_grow(self) -> None:
        from scripts.report_context_budget import measure_context_budget

        report = measure_context_budget(
            rulers_dir="documents/rulers",
            domains=["backend"], include_token_trend=False,
        )
        gm = report["growth"]["managed_1_to_100"]
        gr = report["growth"]["reconcile_0_to_20"]
        self.assertEqual(gm["delta_bytes"], 0)
        self.assertTrue(gm["pass"])
        self.assertEqual(gr["delta_bytes"], 0)
        self.assertTrue(gr["pass"])

    def test_development_source_is_not_a_healthy_runtime(self) -> None:
        from scripts.report_context_budget import measure_context_budget

        report = measure_context_budget(project_root=ROOT, include_token_trend=False)
        self.assertFalse(report["all_pass"])
        self.assertFalse(report["checks"][0]["pass"])

    def test_runtime_fixture_is_validated_and_removed(self) -> None:
        from scripts.runtime_fixture import runtime_fixture

        with runtime_fixture(rulers_dir="documents/test-rulers", domains=["backend"]) as project:
            self.assertNotEqual(ROOT, project)
            self.assertTrue((project / "documents/test-rulers/RULERS_STATE.json").is_file())
        self.assertFalse(project.exists())


class SkillPackageParityTest(unittest.TestCase):
    def test_package_matches_skill_source_exactly(self) -> None:
        local = {
            str(path.relative_to(SKILL_ROOT)): path.read_bytes()
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
            and path.name != ".DS_Store"
            and "__pycache__" not in path.parts
            and not path.name.endswith(".pyc")
            and path.relative_to(SKILL_ROOT).parts[0] != "evals"
        }
        with ZipFile(PACKAGE) as archive:
            packed = {
                name.removeprefix("ai-rulers-init/"): archive.read(name)
                for name in archive.namelist()
                if not name.endswith("/")
            }

        self.assertEqual(set(local), set(packed))
        for relative in sorted(local):
            with self.subTest(relative=relative):
                self.assertEqual(local[relative], packed[relative])


if __name__ == "__main__":
    unittest.main()
