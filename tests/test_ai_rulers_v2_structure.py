from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ai-rulers-init"


class SkillV2StructureTest(unittest.TestCase):
    def test_skill_entry_is_a_lean_lifecycle_orchestrator(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")

        self.assertLessEqual(len(text.splitlines()), 150)
        self.assertIn("scripts/rulers_init.py init-plan", text)
        self.assertIn("scripts/rulers_init.py init-apply", text)
        self.assertIn("references/initialization.md", text)
        self.assertIn("references/discovery.md", text)
        self.assertIn("references/incremental.md", text)
        self.assertNotIn("Step 6: 初始化后清理", text)
        self.assertNotIn("PROJECT_PROFILE.md 已存在：增量模式", text)

    def test_bootstrap_manuals_live_in_references_not_runtime_templates(self) -> None:
        expected_references = (
            "lifecycle.md",
            "discovery.md",
            "generation.md",
            "activation.md",
            "incremental.md",
            "migration-v1.md",
            "root-entry-merge.md",
        )
        for relative in expected_references:
            with self.subTest(relative=relative):
                self.assertTrue((SKILL / "references" / relative).is_file())

        self.assertFalse((SKILL / "templates" / "bootstrap").exists())
        self.assertFalse((SKILL / "templates" / "PROJECT_PROFILE.template.md").exists())
        self.assertFalse((SKILL / "templates" / "AGENTS.md").exists())

    def test_security_and_delivery_runtime_templates_are_complete(self) -> None:
        registry = json.loads(
            (SKILL / "templates" / "domain-registry.json").read_text(encoding="utf-8")
        )["domains"]
        runtime_domains = SKILL / "templates" / "runtime" / "domains"

        for domain in ("security", "delivery"):
            for filename in registry[domain]["templates"]:
                with self.subTest(domain=domain, filename=filename):
                    self.assertTrue((runtime_domains / domain / filename).is_file())

    def test_runtime_core_uses_state_as_activation_authority(self) -> None:
        core = SKILL / "templates" / "runtime" / "core"
        hard_constraints = (core / "HARD_CONSTRAINTS.md").read_text(encoding="utf-8")
        workflow = (core / "WORKFLOW.md").read_text(encoding="utf-8")

        self.assertIn("RULERS_STATE.json", hard_constraints)
        self.assertIn("RULERS_STATE.json", workflow)
        self.assertIn("Context", hard_constraints)
        self.assertIn("机器权威", (SKILL / "templates/runtime/AGENTS.md.tmpl").read_text(encoding="utf-8"))
        self.assertNotIn("存在时的 `PROJECT_PROFILE.md`", workflow)

    def test_trigger_evals_cover_positive_and_negative_near_misses(self) -> None:
        evals = json.loads(
            (SKILL / "evals" / "trigger-evals.json").read_text(encoding="utf-8")
        )

        positives = [item for item in evals if item["should_trigger"]]
        negatives = [item for item in evals if not item["should_trigger"]]
        self.assertGreaterEqual(len(positives), 10)
        self.assertGreaterEqual(len(negatives), 10)
        self.assertTrue(any("PROJECT_PROFILE" in item["query"] for item in negatives))


class ActiveTerminologyTest(unittest.TestCase):
    """Active assets must not reference the removed incremental flow."""

    _LEGACY_PATTERNS = [
        re.compile(r"incremental_pending"),
        re.compile(r"upgrade_pending"),
        re.compile(r"rulers_init.pys+incremental"),
    ]

    _WHITELIST: dict[str, list[re.Pattern[str]]] = {
        "skills/ai-rulers-init/references/lifecycle.md": [
            re.compile(r"incremental_pending|upgrade_pending"),
        ],
        "skills/ai-rulers-init/references/migration-v1.md": [
            re.compile(r"incremental_pending"),
        ],
        "skills/ai-rulers-init/references/incremental.md": [
            re.compile(r"."),
        ],
        "skills/ai-rulers-init/scripts/rulers_lib/incremental.py": [
            re.compile(r"."),
        ],
        "skills/ai-rulers-init/scripts/rulers_lib/migration.py": [
            re.compile(r"incremental_pending|upgrade_pending"),
        ],
        "skills/ai-rulers-init/scripts/rulers_lib/plans.py": [
            re.compile(r"incremental_pending|upgrade_pending"),
        ],
        "CHANGELOG.md": [
            re.compile(r"."),
        ],
    }

    def test_active_assets_have_no_legacy_incremental_flow(self) -> None:
        scan_roots = [
            SKILL / "SKILL.md",
            SKILL / "references",
            SKILL / "templates",
            SKILL / "scripts",
            ROOT / "README.md",
            ROOT / "README-zh.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "CONTRIBUTING-zh.md",
        ]
        violations: list[str] = []
        for scan_root in scan_roots:
            if scan_root.is_file():
                files = [scan_root]
            elif scan_root.is_dir():
                files = sorted(scan_root.rglob("*"))
            else:
                continue
            for path in files:
                if not path.is_file():
                    continue
                if path.suffix in (".pyc",):
                    continue
                if "__pycache__" in path.parts:
                    continue
                if path.name == ".DS_Store":
                    continue
                rel = path.relative_to(ROOT).as_posix()
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                for pattern in self._LEGACY_PATTERNS:
                    for match in pattern.finditer(text):
                        whitelisted = False
                        for wl_path, wl_patterns in self._WHITELIST.items():
                            if rel == wl_path or rel.startswith(wl_path + "/"):
                                if any(wp.search(match.group()) for wp in wl_patterns):
                                    whitelisted = True
                                    break
                        if not whitelisted:
                            violations.append(f"{rel}: {match.group()!r}")
        self.assertEqual(violations, [], f"Legacy incremental references found: {violations}")


if __name__ == "__main__":
    unittest.main()
