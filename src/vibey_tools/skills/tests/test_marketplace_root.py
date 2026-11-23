# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The marketplace folder, its plugins and its manifest are found from a source checkout; the
installed layout is checked against the built wheel by vibey-engine's
tests/meta/test_wheel_ships_default_marketplace.py."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import vibey_skills

TENANT = Path(__file__).resolve().parents[1]


class MarketplaceRootTests(unittest.TestCase):
    def test_a_checkout_is_its_own_marketplace_root(self) -> None:
        root = vibey_skills.marketplace_root()
        self.assertEqual(root, TENANT)
        self.assertEqual(vibey_skills.plugins_root(), TENANT / "plugins")
        self.assertEqual(
            vibey_skills.marketplace_manifest_path(),
            TENANT / ".claude-plugin" / "marketplace.json",
        )

    def test_a_packaged_marketplace_is_preferred(self) -> None:
        packaged = TENANT.parent / "installed" / "vibey_skills"
        with (
            patch.object(vibey_skills, "_PACKAGE_DIR", packaged),
            patch.object(Path, "is_file", lambda self: True),
            patch.object(Path, "is_dir", lambda self: True),
        ):
            self.assertEqual(vibey_skills.marketplace_root(), packaged / "marketplace")

    def test_a_missing_marketplace_says_so(self) -> None:
        with (
            patch.object(vibey_skills, "_PACKAGE_DIR", Path("/nonexistent/vibey_skills")),
            patch.object(vibey_skills, "_REPO_ROOT", Path("/nonexistent")),
            self.assertRaisesRegex(FileNotFoundError, "installation looks incomplete"),
        ):
            vibey_skills.marketplace_root()


if __name__ == "__main__":
    unittest.main()
