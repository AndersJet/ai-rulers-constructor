"""Public lifecycle evidence for two distinct project policies."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_interop_eval import prepare

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/ai-rulers-init"


class InteropFixtureTest(unittest.TestCase):
    def test_policies_stay_in_project_authority_and_repeated_plan_is_noop(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            skills = base / "input-skills"
            for name in ("wayfinder", "research", "grilling", "grill-with-docs", "domain-modeling"):
                folder = skills / name
                folder.mkdir(parents=True)
                (folder / "SKILL.md").write_text(f"Synthetic {name} input.\n")
            for strategy, branch in (("detached", "topic/decision-map"), ("named", "task/map")):
                with self.subTest(strategy=strategy):
                    target = base / strategy
                    policy = "strict-cn" if strategy == "named" else "project-native"
                    evidence = prepare(SKILL, target, strategy=strategy, scenario="rebuild", skills=skills, policy=policy)
                    self.assertFalse(json.loads(evidence["checks"]["context"])["blocked"])
                    self.assertEqual("noop", json.loads(evidence["checks"]["repeat_plan"])["operation"])
                    self.assertIn(branch, evidence["before"]["branches"])
                    self.assertNotIn("refs/remotes", evidence["before"]["branches"])
                    profile = (target / "documents/rulers/PROJECT_PROFILE.md").read_text()
                    workflow = (target / "documents/rulers/core/WORKFLOW.md").read_text()
                    self.assertIn("docs/agents/workflow.md", profile)
                    for project_branch in ("topic/decision-map", "task/map"):
                        self.assertNotIn(project_branch, profile + workflow)
                    self.assertNotIn("skill-interop.md", evidence["checks"]["load"])
                    self.assertIn("personal-draft.txt", evidence["before"]["files"])
                    state = json.loads((target / "documents/rulers/RULERS_STATE.json").read_text())
                    self.assertEqual(policy, state["policy"]["id"])
                    with self.assertRaises(ValueError):
                        prepare(SKILL, target, strategy=strategy, scenario="chart", skills=skills)


if __name__ == "__main__":
    unittest.main()
