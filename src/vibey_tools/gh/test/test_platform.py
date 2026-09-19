# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[platform]`, the forge-neutral nouns, and the selector that turns one into an adapter.

`[platform]` is live configuration, not a table waiting for a reader: `kind` chooses the
adapter the clean-repo survey asks, `host` reaches `gh` as `GH_HOST`, and a kind with no
adapter is refused at load with a sentence saying so.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

from vibey_gh import doctor, tidy
from vibey_gh.config import ADAPTED_PLATFORM_KINDS, GhConfig, PlatformConfig, load_config
from vibey_gh.forge import (
    ChangeRequest,
    CheckResult,
    ForgeComment,
    ForgeKind,
    ForgeLabel,
    ForgeRelease,
    ForgeRepository,
    ProtectedRef,
)
from vibey_gh.forge_github import GitHubForge
from vibey_gh.forge_selector import ForgeSelector
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_selector_interface import ForgeSelectorInterface


def _config(root: Path, text: str) -> GhConfig:
    (root / ".vibey-gh.toml").write_text(text, encoding="utf-8")
    return load_config(root)


# ----------------------------------------------------------------------- the nouns


def test_the_standard_names_three_forges():
    assert [kind.value for kind in ForgeKind] == ["github", "gitlab", "forgejo"]
    assert ForgeKind("gitlab") is ForgeKind.GITLAB


def test_a_repository_is_named_by_its_whole_namespace():
    project = ForgeRepository(ForgeKind.GITLAB, "gitlab.example", "group/subgroup", "tool")
    assert project.full_name == "group/subgroup/tool"


def test_a_release_is_known_by_its_tag_or_else_its_title():
    assert ForgeRelease(tag="v1", name="One").label == "v1"
    assert ForgeRelease(tag="", name="Untitled").label == "Untitled"
    assert ForgeRelease(tag="") == ForgeRelease(tag="", name="", draft=False)


def test_an_unfinished_check_has_no_conclusion_to_mistake_for_a_pass():
    assert CheckResult(name="CI", head_sha="abc").conclusion == ""


@pytest.mark.parametrize(
    "noun",
    [
        ChangeRequest(number=7, head_ref="topic", head_sha="abc", base_ref="develop"),
        ForgeComment(id="IC_1", author="someone", body="hello"),
        CheckResult(name="CI", head_sha="abc", conclusion="success"),
        ForgeRelease(tag="v1"),
        ForgeLabel(name="bug"),
        ProtectedRef(ref="main"),
        ForgeRepository(ForgeKind.GITHUB, "github.com", "o", "r"),
    ],
)
def test_every_noun_is_a_value_that_cannot_be_changed_in_place(noun):
    field = dataclasses.fields(noun)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(noun, field, "changed")


# --------------------------------------------------------------------- `[platform]`


def test_the_default_platform_is_github_on_github_com(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.platform == PlatformConfig(kind="github", host="github.com")


def test_the_platform_table_is_read(tmp_path):
    cfg = _config(tmp_path, '[platform]\nkind = "github"\nhost = "ghe.example.com:8443"\n')
    assert cfg.platform == PlatformConfig(kind="github", host="ghe.example.com:8443")


@pytest.mark.parametrize("kind", ["gitlab", "forgejo"])
def test_a_forge_without_an_adapter_is_refused_at_load_and_says_so(tmp_path, kind):
    with pytest.raises(ValueError) as refused:
        _config(tmp_path, f'[platform]\nkind = "{kind}"\n')
    assert str(refused.value) == (
        f"platform.kind = {kind!r}: the {kind} adapter is not implemented yet; "
        "vibey-gh drives github only (#138)"
    )


@pytest.mark.parametrize("kind", ["bitbucket", "GitHub", "", 3])
def test_a_forge_the_standard_does_not_name_is_refused(kind):
    with pytest.raises(ValueError, match="platform.kind must be one of github, gitlab, forgejo"):
        PlatformConfig(kind=kind)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "host",
    ["", "https://ghe.example.com", "ghe.example.com/api", "ghe example", " ghe", "-ghe", 443],
)
def test_a_host_is_a_bare_host_name(host):
    with pytest.raises(ValueError, match="platform.host must be a bare host name"):
        PlatformConfig(host=host)  # type: ignore[arg-type]


def test_doctor_knows_every_platform_key_and_names_a_stray(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        '[pr_automation]\nenabled = false\n[platform]\nkind = "github"\nhost = "github.com"\n',
        encoding="utf-8",
    )
    assert not [f for f in doctor.diagnose(root=tmp_path) if "platform" in f.message]
    (tmp_path / ".vibey-gh.toml").write_text(
        '[pr_automation]\nenabled = false\n[platform]\nforge = "github"\n', encoding="utf-8"
    )
    messages = [f.message for f in doctor.diagnose(root=tmp_path)]
    assert "[platform] forge is not a key vibey-gh reads; it is silently ignored" in messages


# ----------------------------------------------------------------------- selection


def test_the_selector_is_the_declared_seam_and_adapts_exactly_what_config_accepts():
    selector = ForgeSelector()
    assert isinstance(selector, ForgeSelectorInterface)
    assert selector.kinds == {ForgeKind(kind) for kind in ADAPTED_PLATFORM_KINDS}


def test_github_on_github_com_leaves_gh_to_find_its_own_host(tmp_path):
    forge = ForgeSelector().select(GhConfig(root=tmp_path))
    assert isinstance(forge, ForgeAdapterInterface)
    assert forge == GitHubForge(root=tmp_path, transport=GhTransport(host=None))


def test_any_other_host_pins_gh_to_it(tmp_path):
    cfg = _config(tmp_path, '[platform]\nhost = "ghe.example.com"\n')
    forge = ForgeSelector().select(cfg)
    assert forge == GitHubForge(root=tmp_path, transport=GhTransport(host="ghe.example.com"))


def test_a_kind_the_selector_cannot_build_is_refused_with_the_same_sentence(tmp_path):
    with pytest.raises(ValueError) as refused:
        ForgeSelector(adapters={}).select(GhConfig(root=tmp_path))
    assert str(refused.value) == PlatformConfig.not_adapted("github")


def test_the_selector_builds_whatever_adapter_is_registered_for_the_kind(tmp_path):
    built: list[GhConfig] = []

    def factory(cfg: GhConfig) -> ForgeAdapterInterface:
        built.append(cfg)
        return GitHubForge(root="elsewhere")

    cfg = GhConfig(root=tmp_path)
    forge = ForgeSelector(adapters={ForgeKind.GITHUB: factory}).select(cfg)
    assert forge == GitHubForge(root="elsewhere") and built == [cfg]


def test_unenabled_platform_factories_still_build_their_injected_seams(tmp_path):
    from vibey_gh.forge_forgejo import ForgejoForge
    from vibey_gh.forge_gitlab import GitLabForge
    from vibey_gh.forgejo_transport import ForgejoTransport
    from vibey_gh.gitlab_transport import GitLabTransport

    cfg = GhConfig(root=tmp_path)
    gitlab = ForgeSelector._gitlab(cfg)
    forgejo = ForgeSelector._forgejo(cfg)
    assert isinstance(gitlab, GitLabForge)
    assert isinstance(gitlab.transport, GitLabTransport)
    assert isinstance(forgejo, ForgejoForge)
    assert isinstance(forgejo.transport, ForgejoTransport)


# --------------------------------------------------------- the host reaches the client


@pytest.fixture
def echoing_gh(tmp_path, monkeypatch) -> None:
    """A `gh` that prints the `GH_HOST` it was started with, and nothing else."""
    bin_dir = tmp_path / "echo-bin"
    bin_dir.mkdir()
    executable = bin_dir / "gh"
    executable.write_text(
        f"#!{sys.executable}\nimport os, sys\n"
        "sys.stdout.write(os.environ.get('GH_HOST', '<unset>'))\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))


def test_a_pinned_host_reaches_gh_as_gh_host(echoing_gh, monkeypatch):
    monkeypatch.setenv("GH_HOST", "ambient.example")
    assert GhTransport(host="ghe.example.com").run(["api", "user"]).stdout == "ghe.example.com"


def test_no_host_leaves_the_environment_as_it_was(echoing_gh, monkeypatch):
    monkeypatch.delenv("GH_HOST", raising=False)
    assert GhTransport().run(["api", "user"]).stdout == "<unset>"
    monkeypatch.setenv("GH_HOST", "ambient.example")
    assert GhTransport().run(["api", "user"]).stdout == "ambient.example"


# ------------------------------------------------ the survey asks whichever forge it is given


class Forge:
    """A forge double: the survey must reach it through the two verbs and nothing else."""

    def __init__(self, heads: frozenset[str], releases: tuple[ForgeRelease, ...]) -> None:
        self.heads, self.listed = heads, releases
        self.asked: list[tuple[str, int]] = []

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        self.asked.append(("heads", limit))
        return self.heads, ""

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        self.asked.append(("releases", limit))
        return self.listed, ""


def test_the_survey_is_forge_neutral(fake_gh, tmp_path):
    """Handed a forge, the survey asks it and never runs `gh` at all."""
    import subprocess

    origin = tmp_path / "o.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work = tmp_path / "w"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    for args in (
        ("config", "user.email", "t@example.com"),
        ("config", "user.name", "t"),
        ("commit", "-q", "--allow-empty", "-m", "base"),
        ("branch", "-M", "develop"),
        ("push", "-qu", "origin", "develop"),
        ("push", "-q", "origin", "develop:main"),
        ("push", "-q", "origin", "develop:landed"),
        ("push", "-q", "origin", "develop:live"),
    ):
        subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)
    forge = Forge(frozenset({"live"}), (ForgeRelease(tag="v2", draft=True), ForgeRelease("v1")))
    report = tidy.survey(GhConfig(root=work), local=False, refresh=False, forge=forge)
    assert forge.asked == [("heads", 200), ("releases", 100)]
    assert report.remote_merged == ("landed",)
    assert report.draft_releases == ("v2",)
    assert fake_gh.invocations() == []
