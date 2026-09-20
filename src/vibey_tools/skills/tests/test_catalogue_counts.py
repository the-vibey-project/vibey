# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The catalogue counts this repository states about itself must be true.

Every doc surface here advertises how many plugins and how many skills the marketplace
holds. Those numbers are written by hand in a dozen places and are wrong the moment a
plugin lands, so they drift silently and in generations: before this test existed the tree
simultaneously claimed 127/644 (mkdocs, properdocs, the agent-surface READMEs, the docs
site), 130/665 (README, CLAUDE.md, AGENTS.md, CONTRIBUTING.md, pyproject) and 131/672
(reality). A reader cannot tell which generation they are looking at, and a marketplace
whose own front page miscounts its contents undermines every other claim on the page.

The fix is not to remember harder. It is to make the build fail.

`docs/paper.md` is deliberately excluded: it reports `n = 644 skill documents` as the
corpus size of a specific retrieval evaluation, which is a dated research measurement
rather than a claim about the marketplace as it stands today. Changing it would falsify
the paper, not correct it.

What makes a number a COUNT CLAIM, and why the rule is not "a number near the word
plugin": a claim is a number standing where the catalogue's noun goes. Two shapes do
that. The number sits immediately BEFORE the noun — `135 plugins`, `710 skills` — which is
what these patterns started as and all they could see. Or the noun is ELIDED and the number
is introduced by a determiner pointing back at it: "every plugin in the family: these 134
and vibey-gh's four". The second is a claim about the catalogue exactly as much as the
first, and it is how README.md came to state 134 against a tree of 135 while this suite
passed nineteen times out of nineteen.

The determiner is what keeps the widened rule from swallowing the file. A version number
and a section reference FOLLOW their noun — `version 2.0.0`, `ADR-0034`, `Python 3.12`,
`step 3`, `Requirement 11.6.1` — they never replace it, so no `these`/`those`/`all` ever
introduces one, and a bare `134` on its own is still ignored. The noun deciding WHICH
population is counted must appear in the same clause, within a short phrase and no sentence
end between, which is why the elided form is anchored to "plugin" or "skill" rather than
left to float: `all 710` on a line about skills must not be read as a plugin count and fail
a test it has no business being in.

Anchoring is not enough on its own, because these two nouns travel together — a sentence
about the marketplace names both far more often than it names one. So the anchor is
EXCLUSIVE in both directions, and each half answers a way one sentence was read as two
claims:

- The RIVAL noun may not sit between the anchor and the determiner. "Each plugin ships its
  own skills: all 710 of them" is a true sentence that both patterns matched, charging 710
  to the plugins as well and failing the plugin test with "says 710 plugins, not 135".
  Forbidding the crossing makes the NEAREST noun the anchor, which is the one the determiner
  is actually pointing back at.
- The number may not be immediately followed by the rival noun, because then nothing was
  elided: "Each plugin ships all 12 skills" states its noun outright, and the population it
  states is the other one. The direct `<number> <noun>` rule above is what reads that shape;
  the elided rule exists only for the sentence where the noun is missing.

Neither guard weakens the claim the file makes about itself. A stale count is still caught
in every shape a doc surface writes one; what stops being caught is a count that was never
this population's to begin with.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A line may state a count that was true at some past moment — the 2.0.0 rename note, for
# instance, records that 18 plugins and 71 skills carried over from vibe-engineering-skills.
# Marking it is better than widening the patterns, because the marker says out loud that the
# number is history and must NOT be updated when the catalogue grows.
HISTORICAL = "counts:historical"

# Surfaces that state a count about the marketplace *as it is now*.
SURFACES = (
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "mkdocs.yml",
    "properdocs.yml",
    "docs/index.md",
    "docs/usage.md",
    "docs/rag-context-engine-plan.md",
    ".claude/skills/README.md",
    ".agents/skills/README.md",
    "docs/gen_reference.py",
    "docs/hooks.py",
    ".claude-plugin/marketplace.json",
)


def _elided(noun: str, rival: str) -> str:
    """A count whose noun is ELIDED, introduced by a determiner pointing back at `noun`.

    `{0,60}` keeps the noun and the number in one clause and `[^.]` keeps them in one
    sentence, so the noun is what the number counts rather than a word that happened to be
    nearby. `rival` is the OTHER catalogue noun, and it is excluded twice: it may not be
    crossed on the way to the determiner, and it may not follow the number. Both are what
    make one sentence naming plugins and skills a claim about one of them instead of the
    same figure charged to both. See the module docstring for the sentences that taught it.
    """
    return (
        rf"{noun}(?:(?!{rival})[^.]){{0,60}}?"
        rf"\b(?:these|those|all)\s+(\d{{2,4}})\b(?!\s+{rival}s?)"
    )


# A number immediately followed by a noun that can only mean "plugins in this marketplace",
# or elided after one.
PLUGIN_CLAIMS = (
    re.compile(r"(\d{2,4})\s+(?:Claude Code\s+|Codex\s+)?plugins\b"),
    re.compile(r"Agent Skills across\s+(\d{2,4})\b"),
    re.compile(_elided("plugin", "skill"), re.IGNORECASE),
)

# A number immediately followed by a noun that can only mean "skills in this marketplace",
# or elided after one.
SKILL_CLAIMS = (
    re.compile(r"(\d{2,4})\s+(?:Agent |long-form |evidence-grounded practitioner )?[Ss]kills?\b"),
    re.compile(r"(\d{2,4})\s+evidence-grounded practitioner\b"),
    re.compile(r"(\d{2,4})\s+SKILL\.md\b"),
    re.compile(r"(\d{2,4})\s+pages\b"),
    re.compile(r"(\d{2,4})-document skill corpus\b"),
    re.compile(_elided("skill", "plugin"), re.IGNORECASE),
)


# One row of the root README plugin table: name, version, category, skill count.
README_ROW = re.compile(r"^\| \[([a-z0-9-]+)\]\([^)]+\) \| ([^|]+?) \| ([^|]+?) \| (\d+) \|", re.M)


# Module-level rather than a method on the TestCase because the rule has to be exercised
# against a *synthetic* table: a method reading the real README could only ever show the
# guard passing, which is the one outcome that proves nothing about whether it can fail.
def _duplicate_plugin_rows(markdown: str) -> list[str]:
    """Plugin names the README table lists on more than one row.

    Keying a dict by plugin name collapses duplicates silently — a table listing a plugin
    twice still yields one entry per name, so both set comparisons against the manifest
    pass and the second row is invisible. Counting the names before they become keys is
    what makes a duplicate detectable at all.
    """
    names = [m.group(1) for m in README_ROW.finditer(markdown)]
    return sorted({name for name in names if names.count(name) > 1})


def _claims(patterns: tuple[re.Pattern[str], ...], line: str) -> list[int]:
    """Every count `patterns` read out of one line.

    Shared by the surface sweeps and by the synthetic test below, so the rule the tests
    prove is the rule the build runs. A second copy written for testing would be a second
    rule, and the one that drifts is always the one nobody reads.
    """
    return [int(claim) for pattern in patterns for claim in pattern.findall(line)]


def _true_counts() -> tuple[int, int]:
    manifest = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    plugins = len(manifest["plugins"])
    skills = len(list(ROOT.glob("plugins/*/skills/*/SKILL.md")))
    return plugins, skills


class CatalogueCountTests(unittest.TestCase):
    def test_the_manifest_lists_every_plugin_directory(self) -> None:
        manifest = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        listed = {p["name"] for p in manifest["plugins"]}
        on_disk = {p.parent.parent.name for p in ROOT.glob("plugins/*/.claude-plugin/plugin.json")}
        self.assertEqual(
            listed,
            on_disk,
            "marketplace.json and plugins/ disagree about which plugins exist",
        )

    def test_every_stated_plugin_count_is_true(self) -> None:
        plugins, _ = _true_counts()
        wrong: list[str] = []
        for name in SURFACES:
            path = ROOT / name
            if not path.exists():
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if HISTORICAL in line:
                    continue
                for claim in _claims(PLUGIN_CLAIMS, line):
                    if claim != plugins:
                        wrong.append(f"{name}:{line_no} says {claim} plugins, not {plugins}")
        self.assertEqual(wrong, [], "stale plugin counts:\n  " + "\n  ".join(wrong))

    def test_every_stated_skill_count_is_true(self) -> None:
        _, skills = _true_counts()
        wrong: list[str] = []
        for name in SURFACES:
            path = ROOT / name
            if not path.exists():
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if HISTORICAL in line:
                    continue
                for claim in _claims(SKILL_CLAIMS, line):
                    if claim != skills:
                        wrong.append(f"{name}:{line_no} says {claim} skills, not {skills}")
        self.assertEqual(wrong, [], "stale skill counts:\n  " + "\n  ".join(wrong))

    def test_a_count_claim_with_its_noun_elided_is_caught(self) -> None:
        """The shape that walked past this guard while the catalogue grew underneath it.

        README.md said "every plugin in the family: these 134 and vibey-gh\'s four" against a
        tree of 135, and nothing failed: the number is followed by "and", so a rule that only
        reads `<number> plugins` could not see it at all -- the guard written to stop counts
        drifting carried a stale one inside its own README, through nineteen passing tests.

        The second half is the cost of widening it. These two nouns share almost every
        sentence in these docs, and an anchor that only had to appear SOMEWHERE earlier let
        both patterns fire on one line: "Each plugin ships its own skills: all 710 of them"
        charged 710 to the plugins too and failed the plugin test on a true sentence. A rival
        noun between the anchor and the determiner now disqualifies that anchor, so the
        nearest noun wins and one sentence is one claim about one population.

        Synthetic lines rather than the real files, for the reason `_duplicate_plugin_rows`
        is tested that way: reading a corrected README can only ever show the rule passing,
        which proves nothing about whether it can fail.
        """
        elided = "That one address serves every plugin in the family: these 134 and four more."
        self.assertEqual(_claims(PLUGIN_CLAIMS, elided), [134])
        # The same shape about the other population must not be read as a plugin count, or
        # a true skill claim would fail a test it has no business being in.
        about_skills = "Every skill is installable on its own: all 710 of them, one each."
        self.assertEqual(_claims(SKILL_CLAIMS, about_skills), [710])
        self.assertEqual(_claims(PLUGIN_CLAIMS, about_skills), [])
        self.assertEqual(_claims(SKILL_CLAIMS, elided), [])

        # Both nouns on one line, which is how these docs actually write. The anchor has to
        # be the NEARER noun and fire once, or a true sentence is read as two claims and the
        # build breaks on correct prose with a message asserting a right number is wrong.
        for line, plugins, skills in (
            ("Each plugin ships its own skills: all 710 of them.", [], [710]),
            ("Each plugin ships skills; all 710 of them are installable.", [], [710]),
            ("Every skill lives in a plugin: these 135 and no more.", [135], []),
            ("The skill tree spans every plugin: all 135 of them.", [135], []),
        ):
            self.assertEqual(_claims(PLUGIN_CLAIMS, line), plugins, line)
            self.assertEqual(_claims(SKILL_CLAIMS, line), skills, line)

        # Nothing is elided here -- the noun is stated, and it is the other population's. So
        # the elided rule must not charge 12 to the plugins; the direct `<number> <noun>`
        # rule reads it as the skill figure it literally says, which is that rule's job.
        stated = "Each plugin ships all 12 skills."
        self.assertEqual(_claims(PLUGIN_CLAIMS, stated), [])
        self.assertEqual(_claims(SKILL_CLAIMS, stated), [12])

        # A number that FOLLOWS its noun is not standing in for a population, so none of
        # these is a claim about how many of anything the marketplace holds.
        for quiet in (
            "The plugin marketplace moved to version 2.0.0 in ADR-0034.",
            "See plugin authoring step 3 and Requirement 11.6.1 for the skill layout.",
            "Every plugin here targets Python 3.12, and each skill is one directory.",
        ):
            self.assertEqual(_claims(PLUGIN_CLAIMS, quiet), [], quiet)
            self.assertEqual(_claims(SKILL_CLAIMS, quiet), [], quiet)

    def test_the_readme_table_lists_every_plugin_accurately(self) -> None:
        """CONTRIBUTING.md step 3 for a new plugin: add a row to the root README table.

        Nothing enforced that, so the table drifted exactly as the counts did — it carried
        127 rows against 131 plugins, missing every pack added after the table was last
        rebuilt by hand. The row also states version, category and skill count, and
        CONTRIBUTING requires those to stay accurate, so all three are checked here rather
        than only membership.
        """
        manifest = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        entries = {p["name"]: p for p in manifest["plugins"]}
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        matches = list(README_ROW.finditer(readme))
        rows = {
            m.group(1): (m.group(2).strip(), m.group(3).strip(), int(m.group(4))) for m in matches
        }
        self.assertEqual(
            _duplicate_plugin_rows(readme),
            [],
            "README table lists a plugin on more than one row (CONTRIBUTING.md: one row each)",
        )

        self.assertEqual(
            sorted(set(entries) - set(rows)),
            [],
            "plugins missing a row in the README table (CONTRIBUTING.md step 3)",
        )
        self.assertEqual(
            sorted(set(rows) - set(entries)),
            [],
            "README table lists plugins that are not in the marketplace",
        )

        wrong: list[str] = []
        for name, (version, category, skill_count) in sorted(rows.items()):
            entry = entries[name]
            actual = len(list(ROOT.glob(f"plugins/{name}/skills/*/SKILL.md")))
            if version != entry["version"]:
                wrong.append(f"{name}: table says v{version}, manifest says v{entry['version']}")
            if category != entry.get("category"):
                wrong.append(
                    f"{name}: table says {category}, manifest says {entry.get('category')}"
                )
            if skill_count != actual:
                wrong.append(f"{name}: table says {skill_count} skills, tree has {actual}")
        self.assertEqual(
            wrong, [], "README table disagrees with the tree:\n  " + "\n  ".join(wrong)
        )

    def test_a_duplicated_readme_row_is_caught(self) -> None:
        """A guard nothing has ever seen fail is a guard nobody knows works.

        The duplicate rule cannot be proved against the real README — that table is clean,
        so reading it only ever shows the assertion passing. This feeds the parser a table
        that duplicates a row and asserts it is reported, and, on the same table, that the
        set comparisons the duplicate check backs up stay silent — which is exactly why
        keying rows by plugin name was not enough on its own.
        """
        alpha = "| [alpha](https://example.invalid/alpha) | 0.1.0 | finance | 7 | notes |"
        beta = "| [beta](https://example.invalid/beta) | 0.2.0 | science | 3 | notes |"
        clean = "\n".join([alpha, beta])
        duplicated = "\n".join([alpha, beta, alpha])

        self.assertEqual(_duplicate_plugin_rows(clean), [])
        self.assertEqual(_duplicate_plugin_rows(duplicated), ["alpha"])

        # The membership checks see the same two names either way: they cannot catch this.
        self.assertEqual(
            {m.group(1) for m in README_ROW.finditer(duplicated)},
            {m.group(1) for m in README_ROW.finditer(clean)},
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
