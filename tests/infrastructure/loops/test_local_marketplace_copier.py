# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Copying a marketplace from an absolute folder, without git (SP-LOOPS Task 7)."""

from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

import pytest
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.tree_record import TreeRecord

from vibey.domain.marketplace_source import MARKETPLACE_SOURCE_RULE
from vibey.infrastructure.loops.interfaces.marketplace_fetcher_interface import (
    MarketplaceFetcherInterface,
)
from vibey.infrastructure.loops.local_marketplace_copier import LocalMarketplaceCopier
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.records import FetchResult


def _marketplace(root: Path) -> Path:
    for relative, text in {
        ".claude-plugin/marketplace.json": "{}",
        "plugins/p/skills/s/SKILL.md": "---\nname: s\n---\n",
        "plugins/p/run.sh": "#!/bin/sh\n",
    }.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    (root / "plugins/p/run.sh").chmod(0o755)
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    return root


def test_the_copier_satisfies_its_interface() -> None:
    assert isinstance(LocalMarketplaceCopier(), MarketplaceFetcherInterface)


def test_a_folder_is_copied_without_its_git_metadata_or_its_links(tmp_path: Path) -> None:
    source = _marketplace(tmp_path / "source")
    (source / "plugins/p/link").symlink_to("../../../outside")
    into = tmp_path / "tree"
    result = LocalMarketplaceCopier().fetch(
        MARKETPLACE_SOURCE_RULE.classify(str(source)), None, into
    )
    assert result == FetchResult(None, ("plugins/p/link",))
    assert sorted(p.relative_to(into).as_posix() for p in into.rglob("*")) == [
        ".claude-plugin",
        ".claude-plugin/marketplace.json",
        "plugins",
        "plugins/p",
        "plugins/p/run.sh",
        "plugins/p/skills",
        "plugins/p/skills/s",
        "plugins/p/skills/s/SKILL.md",
    ]
    assert stat.S_IMODE((into / "plugins/p/run.sh").stat().st_mode) == 0o700
    assert stat.S_IMODE(into.stat().st_mode) == 0o700
    assert CapabilityLock().digest_tree(into) != ""


def test_a_ref_is_refused_for_a_folder(tmp_path: Path) -> None:
    source = MARKETPLACE_SOURCE_RULE.classify(str(_marketplace(tmp_path / "s")))
    with pytest.raises(MarketplaceFetchError, match="a local folder has no ref"):
        LocalMarketplaceCopier().fetch(source, "main", tmp_path / "tree")


def test_a_git_source_is_not_this_copiers(tmp_path: Path) -> None:
    source = MARKETPLACE_SOURCE_RULE.classify("https://example.test/x.git")
    with pytest.raises(MarketplaceFetchError, match="not a local folder"):
        LocalMarketplaceCopier().fetch(source, None, tmp_path / "tree")


def test_a_folder_that_cannot_be_read_is_a_fetch_error(tmp_path: Path) -> None:
    source = MARKETPLACE_SOURCE_RULE.classify(str(tmp_path / "missing"))
    with pytest.raises(MarketplaceFetchError, match="cannot be read: .*is not a folder"):
        LocalMarketplaceCopier().fetch(source, None, tmp_path / "tree")


def test_a_folder_past_the_caps_is_refused(tmp_path: Path) -> None:
    source = MARKETPLACE_SOURCE_RULE.classify(str(_marketplace(tmp_path / "s")))
    with pytest.raises(MarketplaceFetchError, match="more than 3 entries"):
        LocalMarketplaceCopier(max_entries=3).fetch(source, None, tmp_path / "tree")
    with pytest.raises(MarketplaceFetchError, match="more than 4 bytes"):
        LocalMarketplaceCopier(max_bytes=4).fetch(source, None, tmp_path / "tree2")


def test_a_file_that_changes_while_it_is_copied_is_refused(tmp_path: Path) -> None:
    root = _marketplace(tmp_path / "s")

    class Swapping(CapabilityLock):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def tree_records(
            self, root: Path, within: Sequence[PurePosixPath] | None = None
        ) -> tuple[TreeRecord, ...]:
            records = super().tree_records(root, within)
            self.calls += 1
            if self.calls == 1:
                (root / "plugins/p/run.sh").write_text("#!/bin/sh\nchanged\n", encoding="utf-8")
            return records

    source = MARKETPLACE_SOURCE_RULE.classify(str(root))
    with pytest.raises(MarketplaceFetchError, match="changed while it was copied"):
        LocalMarketplaceCopier(locker=Swapping()).fetch(source, None, tmp_path / "tree")


def test_a_fifo_in_the_folder_is_refused_and_never_opened(tmp_path: Path) -> None:
    root = _marketplace(tmp_path / "s")
    os.mkfifo(root / "plugins/p/pipe")
    source = MARKETPLACE_SOURCE_RULE.classify(str(root))
    with pytest.raises(MarketplaceFetchError, match="not a file, folder or symlink"):
        LocalMarketplaceCopier().fetch(source, None, tmp_path / "tree")
