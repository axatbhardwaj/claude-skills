import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "testing" / "scripts" / "testing.py"
SKILL_MD = ROOT / "skills" / "testing" / "SKILL.md"


class TestingWorkflowTest(unittest.TestCase):
    def run_step(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd or ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_step_one_uses_portable_script_command_and_state_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_step("--step", "1", "--state-dir", ".testing-state", cwd=cwd)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((cwd / ".testing-state").is_dir())
            self.assertIn(str(SCRIPT), result.stdout)
            self.assertIn("SAVE OUTPUT", result.stdout)
            self.assertNotIn("python3 -m skills.testing.testing", result.stdout)

    def test_dynamic_steps_do_not_emit_empty_subagent_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_step("--step", "2", "--state-dir", ".testing-state", cwd=Path(tmp))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Claude Code", result.stdout)
            self.assertIn("Codex", result.stdout)
            self.assertIn("01-project-context.md", result.stdout)
            self.assertIn("02-coverage-gaps.md", result.stdout)
            self.assertNotIn("Command: \n", result.stdout)
            self.assertNotIn("FIRST ACTION REQUIRED", result.stdout)

    def test_step_four_routes_by_actual_verdict_labels(self) -> None:
        result = self.run_step("--step", "4", "--state-dir", ".testing-state")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VERDICT: ALL CLEAR", result.stdout)
        self.assertIn("VERDICT: ISSUES FOUND", result.stdout)
        self.assertNotIn("ALL agents returned PASS", result.stdout)

    def test_rejects_targets_that_escape_project_scope(self) -> None:
        result = self.run_step("--step", "1", "--target", "../secret")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target", result.stderr)

    def test_skill_markdown_documents_portable_invocation(self) -> None:
        skill = SKILL_MD.read_text()

        self.assertIn("python3 <skill-dir>/scripts/testing.py --step 1", skill)
        self.assertIn("Claude Code", skill)
        self.assertIn("Codex", skill)
        self.assertIn("clawpatch", skill)
        self.assertNotIn("<invoke", skill)
        self.assertNotIn("python3 -m skills.testing.testing", skill)


if __name__ == "__main__":
    unittest.main()
