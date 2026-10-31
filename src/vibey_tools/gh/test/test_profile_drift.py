# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh check --ci`: the live repository settings against `[repository_profile]`."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import cli, install
from vibey_gh.config import GhConfig, PlatformConfig, RepositoryProfileConfig, load_config
from vibey_gh.interfaces.profile_drift_interface import ProfileDriftInterface
from vibey_gh.profile_drift import DESCRIPTION_FALLBACK, ProfileDrift

REPO = "o/r"
TOPICS = ["alpha", "beta"]


def profile(**changes: Any) -> RepositoryProfileConfig:
    return RepositoryProfileConfig(topics=tuple(TOPICS), **changes)


def cfg(tmp_path: Path, kind: str = "github", **changes: Any) -> GhConfig:
    return GhConfig(
        root=tmp_path,
        platform=PlatformConfig(kind=kind),
        repository_profile=profile(**changes),
    )


def live_for(config: GhConfig, **changes: Any) -> dict[str, Any]:
    """The live settings exactly as the declaration says they should be."""
    live: dict[str, Any] = dict(config.repository_profile.settings())
    live.update(
        name="r",
        description=config.repository_profile.description or DESCRIPTION_FALLBACK.format(name="r"),
        topics=list(config.repository_profile.topics),
        _unread={},
    )
    live.update(changes)
    return live


class FakeTransport:
    """Answers `gh api <path>` from a table of path to (returncode, stdout, stderr)."""

    executable = "gh"

    def __init__(self, answers: dict[str, tuple[int, str, str]]) -> None:
        self.answers = answers
        self.calls: list[list[str]] = []

    def run(self, args: Sequence[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        code, out, err = self.answers[args[1]]
        return subprocess.CompletedProcess(list(args), code, out, err)


def served(config: GhConfig, **repo_changes: Any) -> dict[str, tuple[int, str, str]]:
    repo = dict(config.repository_profile.settings())
    for name in ("vulnerability_alerts", "automated_security_fixes"):
        repo.pop(name)
    repo.update(
        name="r",
        description=config.repository_profile.description or DESCRIPTION_FALLBACK.format(name="r"),
    )
    repo.update(repo_changes)
    return {
        f"repos/{REPO}": (0, json.dumps(repo), ""),
        f"repos/{REPO}/topics": (0, json.dumps({"names": TOPICS[::-1]}), ""),
        f"repos/{REPO}/vulnerability-alerts": (0, "", ""),
        f"repos/{REPO}/automated-security-fixes": (0, "", ""),
    }


def drift(config: GhConfig, answers: dict[str, tuple[int, str, str]]):
    return ProfileDrift(transport=FakeTransport(answers), repository=lambda: REPO).survey(config)


# ------------------------------------------------------------------------------ compare


def test_the_class_satisfies_its_declared_seam():
    assert isinstance(ProfileDrift(), ProfileDriftInterface)


def test_a_matching_repository_reports_nothing(tmp_path):
    config = cfg(tmp_path)
    assert ProfileDrift().compare(config, live_for(config)) == ((), ())


def test_a_changed_setting_is_named_with_both_values(tmp_path):
    config = cfg(tmp_path)
    found, unsurveyed = ProfileDrift().compare(config, live_for(config, has_wiki=True))
    assert found == ("has_wiki is True, declared False",)
    assert unsurveyed == ()


def test_an_absent_key_is_not_surveyed_and_never_clean(tmp_path):
    config = cfg(tmp_path)
    live = live_for(config)
    del live["allow_auto_merge"]
    del live["description"]
    del live["topics"]
    found, unsurveyed = ProfileDrift().compare(config, live)
    assert found == ()
    assert unsurveyed == (
        "allow_auto_merge was withheld from this token",
        "description was withheld from this token",
        "topics was withheld from this token",
    )


def test_an_undeclared_squash_title_is_not_compared(tmp_path):
    config = cfg(tmp_path)
    live = live_for(config, squash_merge_commit_title="COMMIT_OR_PR_TITLE")
    assert ProfileDrift().compare(config, live) == ((), ())
    declared = cfg(
        tmp_path, squash_merge_commit_title="PR_TITLE", squash_merge_commit_message="PR_BODY"
    )
    found, _ = ProfileDrift().compare(
        declared, live_for(declared, squash_merge_commit_title="MERGE_MESSAGE")
    )
    assert found == ("squash_merge_commit_title is 'MERGE_MESSAGE', declared 'PR_TITLE'",)


def test_an_empty_description_reads_as_the_workflows_fallback_sentence(tmp_path):
    config = cfg(tmp_path)
    assert ProfileDrift().compare(config, live_for(config, description=None))[0] != ()
    ok = live_for(
        config, description="r — automated delivery, release provenance, and living documentation."
    )
    assert ProfileDrift().compare(config, ok) == ((), ())


def test_a_declared_description_must_match_exactly(tmp_path):
    config = cfg(tmp_path, description="Mine.")
    found, _ = ProfileDrift().compare(config, live_for(config, description="Theirs."))
    assert found == ("description is 'Theirs.', declared 'Mine.'",)


def test_topics_are_a_set_and_order_is_not_drift(tmp_path):
    config = cfg(tmp_path)
    assert ProfileDrift().compare(config, live_for(config, topics=["beta", "alpha"])) == ((), ())
    found, _ = ProfileDrift().compare(config, live_for(config, topics=["alpha"]))
    assert found == ("topics are alpha, declared alpha, beta",)
    found, _ = ProfileDrift().compare(config, live_for(config, topics=[]))
    assert found == ("topics are none, declared alpha, beta",)


def test_a_disabled_profile_is_not_audited(tmp_path):
    config = cfg(tmp_path, enabled=False)
    assert ProfileDrift().compare(config, live_for(config, has_wiki=True)) == ((), ())
    assert ProfileDrift().survey(config) == ((), ())


def test_the_writer_and_the_auditor_share_one_list_of_settings(tmp_path):
    config = cfg(
        tmp_path, squash_merge_commit_title="PR_TITLE", squash_merge_commit_message="PR_BODY"
    )
    managed = config.repository_profile.settings()
    assert set(managed) == set(RepositoryProfileConfig.FLAGS) | set(
        RepositoryProfileConfig.OPTIONAL_TEXT
    )
    workflow = install.render_workflow(install.WORKFLOWS / "repository-profile.yml", config)
    assert json.dumps(managed, separators=(",", ":")) in workflow


# --------------------------------------------------------------------------------- survey


def test_a_repository_that_agrees_with_its_declaration_is_clean(tmp_path):
    config = cfg(tmp_path)
    assert drift(config, served(config)) == ((), ())


def test_a_flipped_setting_is_reported_by_the_survey(tmp_path):
    config = cfg(tmp_path)
    found, unsurveyed = drift(config, served(config, has_wiki=True))
    assert found == ("has_wiki is True, declared False",)
    assert unsurveyed == ()


def test_the_security_endpoints_answer_404_for_off_and_204_for_on(tmp_path):
    config = cfg(tmp_path)
    answers = served(config)
    answers[f"repos/{REPO}/vulnerability-alerts"] = (1, "", "gh: Not Found (HTTP 404)")
    assert drift(config, answers)[0] == ("vulnerability_alerts is False, declared True",)


def test_a_security_endpoint_that_fails_otherwise_is_not_surveyed(tmp_path):
    config = cfg(tmp_path)
    answers = served(config)
    answers[f"repos/{REPO}/automated-security-fixes"] = (1, "", "gh: Forbidden (HTTP 403)")
    found, unsurveyed = drift(config, answers)
    assert found == ()
    assert unsurveyed == ("automated_security_fixes could not be read: gh: Forbidden (HTTP 403)",)


def test_topics_that_cannot_be_read_are_not_surveyed(tmp_path):
    config = cfg(tmp_path)
    answers = served(config)
    answers[f"repos/{REPO}/topics"] = (1, "", "boom")
    assert drift(config, answers)[1] == ("topics could not be read: boom",)
    answers[f"repos/{REPO}/topics"] = (0, "[]", "")
    assert drift(config, answers)[1] == ("topics could not be read: the answer is not an object",)


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ((1, "", "gh: authentication required\nHTTP 401"), "HTTP 401"),
        ((1, "", ""), "no output"),
        ((0, "not json", ""), "the answer is not JSON"),
        ((0, "[]", ""), "the answer is not an object"),
    ],
)
def test_a_repository_that_cannot_be_read_is_one_waiver_not_a_pass(tmp_path, answer, reason):
    config = cfg(tmp_path)
    found, unsurveyed = drift(config, {f"repos/{REPO}": answer})
    assert found == ()
    assert len(unsurveyed) == 1 and unsurveyed[0].startswith(
        "repository settings could not be read:"
    )
    assert reason in unsurveyed[0]


def test_a_missing_gh_is_a_waiver_not_a_pass(tmp_path):
    class NoGh(FakeTransport):
        def run(self, args, **_):
            raise FileNotFoundError(2, "gh")

    result = ProfileDrift(transport=NoGh({}), repository=lambda: REPO).survey(cfg(tmp_path))
    assert result == ((), ("the GitHub CLI (`gh`) is not installed",))


def test_another_forge_is_a_loud_waiver_not_a_pass(tmp_path):
    result = ProfileDrift(transport=FakeTransport({}), repository=lambda: REPO).survey(
        cfg(tmp_path, kind="forgejo")
    )
    assert result == ((), ("repository settings are read from GitHub only (forge forgejo)",))


def test_an_unidentifiable_repository_is_a_waiver(tmp_path):
    def nowhere() -> str:
        raise RuntimeError("no repository here")

    result = ProfileDrift(transport=FakeTransport({}), repository=nowhere).survey(cfg(tmp_path))
    assert result == ((), ("the repository could not be identified: no repository here",))


# ---------------------------------------------------------------------------- the command


class FixedDrift:
    def __init__(self, found: tuple[str, ...], unsurveyed: tuple[str, ...] = ()) -> None:
        self.result = (found, unsurveyed)

    def survey(self, config: GhConfig) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return self.result


def test_fail_check_is_a_key_that_defaults_to_advisory(tmp_path):
    assert RepositoryProfileConfig().fail_check is False
    (tmp_path / ".vibey-gh.toml").write_text("[repository_profile]\nfail_check = true\n")
    assert load_config(tmp_path).repository_profile.fail_check is True
    (tmp_path / ".vibey-gh.toml").write_text("")
    assert load_config(tmp_path).repository_profile.fail_check is False


def test_the_survey_is_made_only_when_asked_for(tmp_path):
    config = cfg(tmp_path)
    assert cli._settings_drift(config, surveyed=False) == ((), ())


@pytest.fixture()
def checkable(tmp_path, monkeypatch):
    """A repository `vibey-gh check` already passes, so only the settings audit can move it."""
    for command in (
        ["git", "init", "-q", "-b", "develop"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "T"],
    ):
        subprocess.run(command, cwd=tmp_path, check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / ".vibey-gh.toml").write_text(
        '[platform]\nkind = "github"\n[fingerprint]\nsources = ["src/*.py"]\n'
        "[documentation]\nenabled = false\n[tidy]\nenabled = false\n"
    )
    (tmp_path / "src" / "a.py").write_text(f"{load_config(tmp_path).header}\nx = 1\n")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["install"]) == 0
    return tmp_path


def audited(monkeypatch, found, unsurveyed=()):
    monkeypatch.setattr(cli, "ProfileDrift", lambda: FixedDrift(found, unsurveyed))


def test_check_ci_prints_the_drift_and_advises_by_default(checkable, monkeypatch, capsys):
    audited(monkeypatch, ("has_wiki is True, declared False",))
    assert cli.main(["check", "--ci"]) == 0
    err = capsys.readouterr().err
    assert "settings drift: has_wiki is True, declared False" in err
    assert "advisory" in err


def test_check_ci_fails_on_drift_once_the_adopter_asks_for_it(checkable, monkeypatch, capsys):
    config = checkable / ".vibey-gh.toml"
    config.write_text(config.read_text() + "[repository_profile]\nfail_check = true\n")
    audited(monkeypatch, ("has_wiki is True, declared False",))
    assert cli.main(["check", "--ci"]) == 1
    err = capsys.readouterr().err
    assert "settings drift: has_wiki is True, declared False" in err
    assert "advisory" not in err
    assert cli.main(["check", "--ci", "--quiet"]) == 1


def test_check_ci_never_counts_an_unsurveyed_setting_as_drift(checkable, monkeypatch, capsys):
    config = checkable / ".vibey-gh.toml"
    config.write_text(config.read_text() + "[repository_profile]\nfail_check = true\n")
    audited(monkeypatch, (), ("topics was withheld from this token",))
    assert cli.main(["check", "--ci"]) == 0
    assert (
        "settings drift: not surveyed — topics was withheld from this token"
        in capsys.readouterr().err
    )


def test_a_quiet_check_skips_a_survey_that_cannot_move_the_exit_code(checkable, monkeypatch):
    def forbidden():
        raise AssertionError("a survey that cannot move the exit code was made")

    monkeypatch.setattr(cli, "ProfileDrift", forbidden)
    assert cli.main(["check", "--ci", "--quiet"]) == 0


def test_a_check_without_ci_makes_no_survey(checkable, monkeypatch):
    def forbidden():
        raise AssertionError("a pre-commit check made forge round trips")

    monkeypatch.setattr(cli, "ProfileDrift", forbidden)
    assert cli.main(["check"]) == 0
