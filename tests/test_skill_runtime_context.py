from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "ai-rulers-init"
TEMPLATES = SKILL_ROOT / "templates" / "runtime"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_rulers.py"


def read_template(relative_path: str) -> str:
    return (TEMPLATES / relative_path).read_text(encoding="utf-8")


class SkillRuntimeContextBudgetTest(unittest.TestCase):
    def test_agents_keeps_only_safety_and_workflow_as_always_loaded_core(self) -> None:
        agents = read_template("AGENTS.md.tmpl")

        self.assertNotRegex(agents, r"6\s*个\s*core\s*文件\*\*必须\*\*全部加载")
        self.assertIn("RULERS_STATE.json", agents)
        self.assertIn("core/HARD_CONSTRAINTS.md", agents)
        self.assertIn("core/WORKFLOW.md", agents)

        constant_core_section = agents.split("## 条件路由", 1)[0]
        self.assertIn("core/HARD_CONSTRAINTS.md", constant_core_section)
        self.assertIn("core/WORKFLOW.md", constant_core_section)
        self.assertNotIn("core/DOC_GOVERNANCE.md", constant_core_section)
        self.assertNotIn("core/RULER_MAINTENANCE.md", constant_core_section)
        self.assertNotIn("core/GIT_COMMIT_CONVENTION.md", constant_core_section)
        self.assertNotIn("core/CHANGELOG_MAINTENANCE.md", constant_core_section)

    def test_high_churn_domain_indexes_route_leaves_conditionally(self) -> None:
        bulk_load_indexes = [
            "domains/backend/INDEX.md",
            "domains/database/INDEX.md",
            "domains/frontend/common/INDEX.md",
            "domains/frontend/web/develop/INDEX.md",
            "domains/frontend/web/design/INDEX.md",
            "domains/frontend/app/develop/INDEX.md",
            "domains/frontend/app/design/INDEX.md",
        ]

        for relative_path in bulk_load_indexes:
            with self.subTest(relative_path=relative_path):
                index_text = read_template(relative_path)
                self.assertNotRegex(index_text, r"##\s+1\.\s*(必读文档|必需文档)")
                self.assertRegex(index_text, r"任务条件\s*\|\s*还需加载")

    def test_non_authoritative_app_design_examples_are_not_default_runtime_rules(self) -> None:
        self.assertFalse(
            (TEMPLATES / "domains" / "frontend" / "app" / "design" / "EXAMPLES.md").exists(),
            "Non-authoritative examples should not ship as a default runtime rule.",
        )
        app_design_index = read_template("domains/frontend/app/design/INDEX.md")
        self.assertNotIn("EXAMPLES.md", app_design_index)
        self.assertNotIn("非权威示例", app_design_index)

    def test_validator_enforces_runtime_context_budget(self) -> None:
        validator = VALIDATOR.read_text(encoding="utf-8")

        self.assertIn("validate_template", validator)
        self.assertIn("--mode", validator)


if __name__ == "__main__":
    unittest.main()
