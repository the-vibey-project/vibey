# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The composition root wires the `[loops]` trust rule to the on-disk table reader."""

from pathlib import Path

from vibey import bootstrap
from vibey.application.loops_bundle_settings import LoopsBundleSettings


def test_the_settings_read_real_files_through_the_toml_reader(tmp_path: Path) -> None:
    settings = bootstrap.loops_bundle_settings()
    assert isinstance(settings, LoopsBundleSettings)
    mine = tmp_path / "mine.toml"
    mine.write_text("[loops]\nplugins = []\n", encoding="utf-8")
    project = tmp_path / "repo.toml"
    project.write_text("[loops]\nmarketplaces = []\n", encoding="utf-8")
    loaded = settings.load(mine, project)
    assert loaded.bundle.plugins == ()
    assert len(loaded.notices) == 1
