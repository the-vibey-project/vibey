# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""tools/validate_manifests.py enforces the ChatGPT plugin limits on skill front matter.

Skill `name` is at most 64 characters and `description` at most 1024. Seventeen skills
shipped over those limits because nothing checked them; these tests pin the check and run
it against the real tree so a future skill cannot regress.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

TENANT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TENANT / "tools"))

from validate_manifests import SkillLimits  # noqa: E402


class SkillLimitsTest(unittest.TestCase):
    def test_limits_are_the_chatgpt_plugin_limits(self) -> None:
        self.assertEqual(SkillLimits.MAX_NAME, 64)
        self.assertEqual(SkillLimits.MAX_DESCRIPTION, 1024)

    def test_values_at_the_limit_pass(self) -> None:
        self.assertEqual(SkillLimits.violations("s", "n" * 64, "d" * 1024), [])

    def test_name_over_the_limit_fails(self) -> None:
        problems = SkillLimits.violations("s", "n" * 65, "ok")
        self.assertEqual(len(problems), 1)
        self.assertIn("name is 65", problems[0])

    def test_description_over_the_limit_fails(self) -> None:
        problems = SkillLimits.violations("s", "ok", "d" * 1025)
        self.assertEqual(len(problems), 1)
        self.assertIn("description is 1025", problems[0])

    def test_both_over_reports_both(self) -> None:
        self.assertEqual(len(SkillLimits.violations("s", "n" * 70, "d" * 2000)), 2)

    def test_the_real_marketplace_is_within_the_limits(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TENANT / "tools" / "validate_manifests.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
