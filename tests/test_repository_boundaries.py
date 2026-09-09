from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "skills" / "ai-rulers-init" / "templates" / "runtime"


def read_root(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def read_ruler(relative_path: str) -> str:
    return (RUNTIME / "domains" / relative_path).read_text(encoding="utf-8")


class RepositoryBoundariesTest(unittest.TestCase):
    def test_development_repository_has_no_self_installation(self) -> None:
        self.assertFalse((ROOT / "documents" / "rulers").exists())
        for entry in ("AGENTS.md",):
            self.assertNotIn("<!-- ai-rulers-init:begin", read_root(entry))

    def test_project_entry_is_self_contained_and_links_exist(self) -> None:
        text = read_root("AGENTS.md")
        self.assertNotIn("documents/rulers/", text)
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            self.assertTrue((ROOT / target.split("#", 1)[0]).exists(), target)
        self.assertIn("subject 使用中文", text)
        self.assertIn("CHANGELOG.md", text)

    def test_runtime_entry_keeps_minimum_core_resident(self) -> None:
        agents = (RUNTIME / "AGENTS.md.tmpl").read_text(encoding="utf-8")
        resident = agents.split("2. 始终读取", 1)[1].split("\n3.", 1)[0]
        self.assertIn("core/HARD_CONSTRAINTS.md", resident)
        self.assertIn("core/WORKFLOW.md", resident)
        self.assertNotIn("core/DOC_GOVERNANCE.md", resident)
        self.assertNotIn("core/RULER_MAINTENANCE.md", resident)

    def test_high_churn_domain_indexes_route_leaves_conditionally(self) -> None:
        bulk_load_indexes = [
            "backend/INDEX.md",
            "database/INDEX.md",
            "frontend/common/INDEX.md",
            "frontend/web/develop/INDEX.md",
            "frontend/web/design/INDEX.md",
            "frontend/app/develop/INDEX.md",
            "frontend/app/design/INDEX.md",
        ]

        for relative_path in bulk_load_indexes:
            with self.subTest(relative_path=relative_path):
                index_text = read_ruler(relative_path)
                self.assertNotRegex(index_text, r"##\s+1\.\s*(必读文档|必需文档)")
                self.assertRegex(index_text, r"任务条件\s*\|\s*还需加载")

    def test_runtime_navigation_defers_to_active_state(self) -> None:
        index = (RUNTIME / "INDEX.md.tmpl").read_text(encoding="utf-8")
        self.assertIn("RULERS_STATE.json", index)
        self.assertIn("未审阅领域不得进入运行态路由", index)

    def test_non_authoritative_app_design_examples_are_not_default_runtime_rules(self) -> None:
        self.assertFalse(
            (RUNTIME / "domains" / "frontend" / "app" / "design" / "EXAMPLES.md").exists(),
            "Non-authoritative examples should not be a default runtime rule.",
        )
        app_design_index = read_ruler("frontend/app/design/INDEX.md")
        self.assertNotIn("EXAMPLES.md", app_design_index)
        self.assertNotIn("非权威示例", app_design_index)



if __name__ == "__main__":
    unittest.main()
