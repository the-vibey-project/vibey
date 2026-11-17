# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every `uses:` in the workflows and composite actions is pinned to a commit SHA, behind a ratchet.

A `uses: owner/repo@v4` is a moving name: whoever controls the tag controls what runs in our
pipeline. `vibey-gh pin-actions --apply` rewrites each one to `@<40-hex commit> # v4`. This census
counts what is still unpinned and holds the count to `tests/meta/unpinned_actions.toml`, a ceiling
that only falls: above it fails, and below it fails too, naming the number to lower it to, so a
fixed use cannot be re-introduced unnoticed (sub-doctrine 12.e).

The count is made by `PinActions.unpinned`, the same rule the command uses (a real `uses:` key;
`run:` block text, comments, `./` local actions and `docker://` references are not counted), so the
test and the tool never disagree.

Checks are module-level functions: pytest collects functions, and ADR-0016 permits that for a
collection contract.
"""

import tomllib
from pathlib import Path

from vibey_gh.pin_actions import PinActions

REPO = Path(__file__).resolve().parents[2]
CEILING = REPO / "tests/meta/unpinned_actions.toml"
PINNED = "a" * 40


def unpinned_count(paths: list[Path]) -> int:
    """How many `uses:` lines across `paths` are not pinned to a commit."""
    pins = PinActions()
    return sum(len(pins.unpinned(path.read_text(encoding="utf-8"), path)) for path in paths)


def _ceiling() -> int:
    return int(tomllib.loads(CEILING.read_text(encoding="utf-8"))["ceiling"])


def test_a_synthetic_unpinned_use_is_counted(tmp_path: Path) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        f"      - uses: actions/setup-node@{PINNED} # v4\n"
        "      - uses: ./.github/actions/local\n"
        "      - uses: docker://alpine:3.20\n"
        "      # - uses: actions/cache@v4\n"
        "      - run: |\n"
        "          echo uses: actions/upload-artifact@v4\n",
        encoding="utf-8",
    )
    assert unpinned_count([workflow]) == 1


def test_the_unpinned_count_never_exceeds_the_ceiling() -> None:
    count = unpinned_count(PinActions.default_paths(REPO))
    assert count <= _ceiling(), (
        f"{count} unpinned uses: exceeds the ceiling of {_ceiling()}; "
        "run `uv run vibey-gh pin-actions --apply`"
    )


def test_the_ceiling_is_exactly_the_count() -> None:
    count = unpinned_count(PinActions.default_paths(REPO))
    assert count == _ceiling(), (
        f"{count} unpinned uses: remain; lower the ceiling to {count} in "
        "tests/meta/unpinned_actions.toml"
    )
