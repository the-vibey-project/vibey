# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[install] pin_version` pins adopters to the release `vibey-gh` runs from.

From 1.0.0 until this module existed, every repository that was not itself the fallback
distribution had its pin dropped without a word: ten adopters that set the key rendered
`pip install --quiet vibey`, floating. These tests state the installed metadata exactly —
through the seam, or through a site directory built in `tmp_path` — so none of them
depends on how the virtualenv running the suite happened to be installed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import vibey_gh
from vibey_gh.config import GhConfig
from vibey_gh.fallback_pin import RUNNING_PACKAGE, FallbackPinResolver, InstalledDistributions
from vibey_gh.install import (
    FALLBACK_DISTRIBUTION,
    FALLBACK_INSTALL,
    WORKFLOWS,
    install,
    installed,
    render_workflow,
    rerender_version_pinned,
)
from vibey_gh.interfaces.fallback_pin_resolver_interface import (
    FallbackPin,
    FallbackPinResolverInterface,
)
from vibey_gh.interfaces.installed_distributions_interface import (
    InstalledDistributionsInterface,
)

PINNED = f'python -m pip install --quiet "{FALLBACK_DISTRIBUTION}==1.0.0"\n'


@dataclass
class Distributions:
    """Installed metadata, stated rather than discovered."""

    versions: dict[str, str] = field(default_factory=dict)
    from_source: set[str] = field(default_factory=set)
    ships_running: set[str] = field(default_factory=set)

    def version(self, distribution: str) -> str | None:
        return self.versions.get(distribution)

    def installed_from_source(self, distribution: str) -> bool:
        return distribution in self.from_source

    def installs(self, distribution: str, path: Path) -> bool:
        return distribution in self.ships_running


class Unasked:
    """Metadata that must not be consulted at all."""

    def version(self, distribution: str) -> str | None:
        raise AssertionError("consulted the installed metadata")

    def installed_from_source(self, distribution: str) -> bool:
        raise AssertionError("consulted the installed metadata")

    def installs(self, distribution: str, path: Path) -> bool:
        raise AssertionError("consulted the installed metadata")


RELEASE = Distributions(
    versions={FALLBACK_DISTRIBUTION: "1.0.0"}, ships_running={FALLBACK_DISTRIBUTION}
)


def _adopter(root: Path, **overrides) -> GhConfig:
    """A repository that merely adopted the tooling, with `pin_version` on."""
    root.joinpath("pyproject.toml").write_text(
        '[project]\nname = "somebody-else"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    return GhConfig(root=root, **{"pin_version": True, **overrides})


def _render(cfg: GhConfig, distributions) -> tuple[FallbackPin, str]:
    pin = FallbackPinResolver(distributions).resolve(cfg)
    return pin, render_workflow(WORKFLOWS / "provenance.yml", cfg, fallback_pin=pin)


def test_the_seams_are_what_the_classes_implement():
    assert isinstance(FallbackPinResolver(), FallbackPinResolverInterface)
    assert isinstance(InstalledDistributions(), InstalledDistributionsInterface)
    assert isinstance(Distributions(), InstalledDistributionsInterface)


def test_the_running_package_is_the_vibey_gh_actually_imported():
    assert RUNNING_PACKAGE == Path(vibey_gh.__file__)


# ------------------------------------------------------------------ the six outcomes


def test_the_repository_that_is_the_fallback_distribution_pins_its_own_release(tmp_path):
    """Self-hosting wins, exactly as before: the installed metadata is never asked."""
    tmp_path.joinpath("pyproject.toml").write_text(
        f'[project]\nname = "{FALLBACK_DISTRIBUTION}"\nversion = "2.3.4"\n', encoding="utf-8"
    )
    pin, text = _render(GhConfig(root=tmp_path, pin_version=True), Unasked())
    assert pin == FallbackPin("2.3.4", from_repository=True)
    assert f'python -m pip install --quiet "{FALLBACK_DISTRIBUTION}==2.3.4"\n' in text


def test_an_adopter_pins_the_installed_release_it_runs_from(tmp_path):
    """The defect: this rendered floating for every adopter from 1.0.0 on."""
    pin, text = _render(_adopter(tmp_path), RELEASE)
    assert pin == FallbackPin("1.0.0")
    assert PINNED in text
    assert FALLBACK_INSTALL not in text
    assert "9.9.9" not in text  # the adopter's own version names no release of the tooling
    # The self-hosting branch is never pinned, for an adopter any more than for vibey.
    assert 'python -m pip install --quiet -e "$self"\n' in text


def test_an_editable_install_floats_and_says_why(tmp_path):
    """An editable checkout claims the last release while its templates may be ahead."""
    distributions = Distributions(
        versions={FALLBACK_DISTRIBUTION: "1.0.0"},
        from_source={FALLBACK_DISTRIBUTION},
        ships_running={FALLBACK_DISTRIBUTION},
    )
    pin, text = _render(_adopter(tmp_path), distributions)
    assert pin.version is None
    assert FALLBACK_INSTALL in text
    assert pin.notice is not None
    assert "source tree" in pin.notice
    assert f"`{FALLBACK_DISTRIBUTION}` 1.0.0" in pin.notice


def test_a_vibey_gh_from_another_distribution_floats_and_says_why(tmp_path):
    distributions = Distributions(versions={FALLBACK_DISTRIBUTION: "1.0.0", "vibey-gh": "1.73.0"})
    pin, text = _render(_adopter(tmp_path), distributions)
    assert pin.version is None
    assert FALLBACK_INSTALL in text
    assert pin.notice is not None
    assert f"not installed by `{FALLBACK_DISTRIBUTION}` 1.0.0" in pin.notice


def test_pin_version_off_floats_without_a_notice_or_a_question(tmp_path):
    pin, text = _render(_adopter(tmp_path, pin_version=False), Unasked())
    assert pin == FallbackPin(None)
    assert FALLBACK_INSTALL in text


def test_missing_metadata_floats_and_says_why(tmp_path):
    pin, text = _render(_adopter(tmp_path), Distributions())
    assert pin.version is None
    assert FALLBACK_INSTALL in text
    assert pin.notice is not None
    assert f"no `{FALLBACK_DISTRIBUTION}` distribution is installed" in pin.notice


def test_every_notice_says_what_to_do_about_it(tmp_path):
    for distributions in (
        Distributions(),
        Distributions(versions={FALLBACK_DISTRIBUTION: "1.0.0"}),
        Distributions(
            versions={FALLBACK_DISTRIBUTION: "1.0.0"}, from_source={FALLBACK_DISTRIBUTION}
        ),
    ):
        notice = FallbackPinResolver(distributions).resolve(_adopter(tmp_path)).notice
        assert notice is not None
        assert notice.startswith("[install] pin_version is set")
        assert "stays floating" in notice
        assert "run vibey-gh from a published release to pin it" in notice


def test_a_renamed_fallback_pins_only_its_own_distribution(tmp_path):
    """`vibey` being installed says nothing about a fork publishing under another name."""
    cfg = _adopter(tmp_path, fallback_package="acme-conductor")
    pin = FallbackPinResolver(RELEASE).resolve(cfg)
    assert pin.version is None
    assert pin.notice is not None
    assert "no `acme-conductor` distribution is installed" in pin.notice

    acme = Distributions(versions={"acme-conductor": "7.1.0"}, ships_running={"acme-conductor"})
    text = _render(cfg, acme)[1]
    assert 'python -m pip install --quiet "acme-conductor==7.1.0"\n' in text


# ------------------------------------------------------- every caller of the pin agrees


def test_install_and_the_drift_check_agree_on_an_adopters_pin(tmp_path):
    cfg = _adopter(tmp_path)
    pin = FallbackPinResolver(RELEASE).resolve(cfg)
    install(cfg, hooks_path=False, fallback_pin=pin)
    deployed = tmp_path / ".github" / "workflows" / "provenance.yml"
    assert PINNED in deployed.read_text(encoding="utf-8")
    assert installed(cfg, local=False, fallback_pin=pin)[0] is True

    # A later release moves the pin: the drift check names the deployed copy, and
    # `install` from that release is what rewrites it.
    later = FallbackPin("1.1.0")
    ok, problems = installed(cfg, local=False, fallback_pin=later)
    assert ok is False
    assert ".github/workflows/provenance.yml is out of date" in problems


def test_a_bump_never_moves_a_pin_the_repository_does_not_own(tmp_path):
    """An adopter's own version decides nothing in these files.

    Re-rendering on its bump would fold a tooling upgrade into a release commit that never
    asked for one; `vibey-gh install` is where an adopter's pin moves.
    """
    cfg = _adopter(tmp_path)
    install(cfg, hooks_path=False, fallback_pin=FallbackPin("1.0.0"))
    before = (tmp_path / ".github" / "workflows" / "provenance.yml").read_text(encoding="utf-8")
    assert rerender_version_pinned(cfg, fallback_pin=FallbackPin("1.1.0")) == []
    after = (tmp_path / ".github" / "workflows" / "provenance.yml").read_text(encoding="utf-8")
    assert after == before


def test_a_bump_still_moves_the_pin_the_repository_owns(tmp_path):
    tmp_path.joinpath("pyproject.toml").write_text(
        f'[project]\nname = "{FALLBACK_DISTRIBUTION}"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    cfg = GhConfig(root=tmp_path, pin_version=True)
    install(cfg, hooks_path=False, fallback_pin=FallbackPin("1.0.0", from_repository=True))
    moved = rerender_version_pinned(cfg, fallback_pin=FallbackPin("1.1.0", from_repository=True))
    assert ".github/workflows/provenance.yml" in moved


# ------------------------------------------------ the metadata, read from a real site


def _site(
    tmp_path: Path,
    *,
    direct_url: str | None = None,
    record: str | None = "vibey_gh/__init__.py,,\n",
) -> Path:
    """A site directory holding `vibey` 1.0.0 and the `vibey_gh` it installed."""
    site = tmp_path / "site"
    info = site / f"{FALLBACK_DISTRIBUTION}-1.0.0.dist-info"
    info.mkdir(parents=True)
    info.joinpath("METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {FALLBACK_DISTRIBUTION}\nVersion: 1.0.0\n",
        encoding="utf-8",
    )
    if record is not None:
        info.joinpath("RECORD").write_text(record, encoding="utf-8")
    if direct_url is not None:
        info.joinpath("direct_url.json").write_text(direct_url, encoding="utf-8")
    site.joinpath("vibey_gh").mkdir()
    site.joinpath("vibey_gh", "__init__.py").write_text("", encoding="utf-8")
    return site


def test_the_real_reader_finds_a_release_on_its_search_path(tmp_path):
    site = _site(tmp_path)
    reader = InstalledDistributions([str(site)])
    assert reader.version(FALLBACK_DISTRIBUTION) == "1.0.0"
    assert reader.installed_from_source(FALLBACK_DISTRIBUTION) is False
    assert reader.installs(FALLBACK_DISTRIBUTION, site / "vibey_gh" / "__init__.py") is True


def test_the_real_reader_and_the_resolver_pin_end_to_end(tmp_path):
    site = _site(tmp_path, direct_url=json.dumps({"url": "file:///w.whl", "archive_info": {}}))
    resolver = FallbackPinResolver(
        InstalledDistributions([str(site)]), running=site / "vibey_gh" / "__init__.py"
    )
    assert resolver.resolve(_adopter(tmp_path)) == FallbackPin("1.0.0")


def test_the_real_reader_answers_for_a_distribution_that_is_not_there(tmp_path):
    reader = InstalledDistributions([str(tmp_path)])
    assert reader.version(FALLBACK_DISTRIBUTION) is None
    assert reader.installed_from_source(FALLBACK_DISTRIBUTION) is False
    assert reader.installs(FALLBACK_DISTRIBUTION, tmp_path / "vibey_gh" / "__init__.py") is False


def test_the_default_reader_searches_the_running_interpreters_path():
    assert InstalledDistributions().version("no-such-distribution-vibey-gh-tests") is None


@pytest.mark.parametrize(
    ("direct_url", "from_source"),
    [
        pytest.param(json.dumps({"url": "file:///w.whl", "archive_info": {}}), False, id="archive"),
        pytest.param(
            json.dumps({"url": "file:///w", "dir_info": {"editable": True}}), True, id="editable"
        ),
        pytest.param(json.dumps({"url": "file:///w", "dir_info": {}}), True, id="directory"),
        pytest.param(
            json.dumps({"url": "https://x/r.git", "vcs_info": {"vcs": "git"}}), True, id="vcs"
        ),
        pytest.param("{not json", True, id="unreadable"),
        pytest.param("[]", True, id="not an object"),
    ],
)
def test_the_real_reader_reads_where_a_distribution_came_from(tmp_path, direct_url, from_source):
    site = _site(tmp_path, direct_url=direct_url)
    verdict = InstalledDistributions([str(site)]).installed_from_source(FALLBACK_DISTRIBUTION)
    assert verdict is from_source


def test_the_real_reader_only_claims_a_file_its_record_lists(tmp_path):
    site = _site(tmp_path, record="vibey/__init__.py,,\nvibey_gh/cli.py,,\n")
    reader = InstalledDistributions([str(site)])
    assert reader.installs(FALLBACK_DISTRIBUTION, site / "vibey_gh" / "__init__.py") is False


def test_the_real_reader_does_not_claim_a_same_named_file_elsewhere(tmp_path):
    site = _site(tmp_path)
    elsewhere = tmp_path / "checkout" / "vibey_gh" / "__init__.py"
    elsewhere.parent.mkdir(parents=True)
    elsewhere.write_text("", encoding="utf-8")
    assert InstalledDistributions([str(site)]).installs(FALLBACK_DISTRIBUTION, elsewhere) is False


def test_the_real_reader_claims_nothing_without_a_record(tmp_path):
    site = _site(tmp_path, record=None)
    reader = InstalledDistributions([str(site)])
    assert reader.installs(FALLBACK_DISTRIBUTION, site / "vibey_gh" / "__init__.py") is False
