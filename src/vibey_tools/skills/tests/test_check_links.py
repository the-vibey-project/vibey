# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""tools/check_links.py resolves this tenant's self-links against the monorepo root.

The checker printed "ok" for as long as this tree has lived in the monorepo while
checking none of the README's repository links (#263). It matched only `/main/`,
the README points at `develop`, and it resolved each path against this folder when
every path is monorepo-relative. These tests build a throwaway checkout, a root with
`.git` and `.vibey-gh.toml` and this tenant nested at its real depth, so each
property is asserted against a layout the checker has to discover rather than one it
is handed.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from check_links import LinkChecker  # noqa: E402

SELF = "https://github.com/the-vibey-project/vibey"
TENANT = Path("src", "vibey_tools", "skills")


class CheckoutTestCase(unittest.TestCase):
    """A fresh repository root per test, with the tenant nested inside it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".git").mkdir()
        self.tenant = self.root / TENANT
        self.tenant.mkdir(parents=True)
        (self.root / "src" / "vibey_tools" / "gh").mkdir()
        (self.root / "src" / "vibey_tools" / "gh" / "README.md").write_text("gh\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def readme(self, text: str) -> None:
        (self.tenant / "README.md").write_text(text, encoding="utf-8")

    def problems(self) -> list[str]:
        return LinkChecker.for_checkout(self.tenant).problems()


class SelfLinkTests(CheckoutTestCase):
    def test_a_develop_link_to_a_real_monorepo_path_passes(self) -> None:
        self.readme(f"[gh]({SELF}/tree/develop/src/vibey_tools/gh/)\n")
        self.assertEqual(self.problems(), [])

    def test_the_path_is_resolved_against_the_repository_root_not_the_tenant(self) -> None:
        # `src/vibey_tools/gh/README.md` exists at the root; under the tenant it does not.
        self.readme(f"[gh]({SELF}/blob/main/src/vibey_tools/gh/README.md)\n")
        self.assertEqual(self.problems(), [])

    def test_a_missing_path_is_reported_on_either_branch(self) -> None:
        for ref in ("develop", "main"):
            with self.subTest(ref=ref):
                self.readme(f"[x]({SELF}/blob/{ref}/src/vibey_tools/skills/NOPE.md)\n")
                (found,) = self.problems()
                self.assertIn("does not exist in the repository", found)

    def test_a_ref_that_is_not_a_long_lived_branch_is_reported_not_skipped(self) -> None:
        self.readme(f"[x]({SELF}/tree/feature-x/src/vibey_tools/gh/)\n")
        (found,) = self.problems()
        self.assertIn("`feature-x`, which is not a long-lived branch", found)

    def test_blob_and_tree_must_match_file_and_directory(self) -> None:
        self.readme(
            f"[d]({SELF}/blob/develop/src/vibey_tools/gh)\n"
            f"[f]({SELF}/tree/develop/src/vibey_tools/gh/README.md)\n"
        )
        found = self.problems()
        self.assertEqual(len(found), 2)
        self.assertIn("is a directory but linked with /blob/", found[0])
        self.assertIn("is a file but linked with /tree/", found[1])

    def test_a_relative_root_doc_link_is_told_the_monorepo_path(self) -> None:
        self.readme("[c](CONTRIBUTING.md)\n")
        (found,) = self.problems()
        self.assertIn(f"{SELF}/blob/develop/src/vibey_tools/skills/CONTRIBUTING.md", found)


class BranchTests(CheckoutTestCase):
    def test_branches_come_from_the_root_vibey_gh_toml(self) -> None:
        (self.root / ".vibey-gh.toml").write_text(
            '[fingerprint]\nintegration = "not-this"\n\n'
            '[branches]\nintegration = "trunk"  # the day-to-day branch\n'
            'release     = "stable"\n\n[merge_train]\nrelease = "nor-this"\n',
            encoding="utf-8",
        )
        self.assertEqual(LinkChecker.read_branch_refs(self.root), ("trunk", "stable"))
        self.readme(f"[gh]({SELF}/tree/trunk/src/vibey_tools/gh/)\n")
        self.assertEqual(self.problems(), [])

    def test_without_the_file_it_means_what_vibey_gh_means(self) -> None:
        self.assertEqual(LinkChecker.read_branch_refs(self.root), ("develop", "main"))


class RepositoryRootTests(unittest.TestCase):
    def test_a_worktree_gitfile_marks_the_root_too(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").write_text("gitdir: elsewhere\n")
            nested = root / TENANT
            nested.mkdir(parents=True)
            self.assertEqual(LinkChecker.find_repository_root(nested), root)

    def test_outside_a_checkout_it_refuses_rather_than_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "loose"
            nested.mkdir()
            probe = Path(tmp)
            while probe != probe.parent:
                if (probe / ".git").exists():
                    self.skipTest(f"{probe} is itself inside a checkout")
                probe = probe.parent
            with self.assertRaises(FileNotFoundError):
                LinkChecker.find_repository_root(nested)


if __name__ == "__main__":
    unittest.main()
