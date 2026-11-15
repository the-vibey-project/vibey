# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The releases the paper counts are a tracked file, and no forge state can change a figure.

The release-cadence figure once read `git tag` whenever it was checked, so deleting a release
tag (2026-11-13) or cutting a new one turned develop red with no commit to blame. The releases
are now `docs/paper_releases.toml`; a tag is read once, by `sync`, to propose an entry, and
`check` says out loud when the release branch ships a version the file lacks.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "paper_releases.py"
LEDGER = REPO / "docs" / "paper_releases.toml"
HEAD = '[[family]]\npackage = "vibey"\ntag_prefix = "vibey-v"\nversion_file = "pyproject.toml"\n'
GIT = [
    "git",
    "-c",
    "user.name=release-test",
    "-c",
    "user.email=release-test@example.invalid",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
]


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run([*GIT, *args], cwd=repo, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--repo", str(repo)],
        check=False,
        capture_output=True,
        text=True,
    )


def _repo(tmp_path: Path, version: str = "1.0.0") -> Path:
    """A repository whose `origin/main` ships `version`, with a ledger that has no releases."""
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n')
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "paper_releases.toml").write_text(HEAD, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "chore: base")
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path


def _entries(repo: Path) -> list[str]:
    ledger = tomllib.loads((repo / "docs" / "paper_releases.toml").read_text("utf-8"))
    return [release["tag"] for release in ledger.get("release", [])]


def test_the_tracked_ledger_is_well_formed() -> None:
    done = _run(REPO, "check", "--release-ref", "refs/does-not-exist")
    assert done.returncode == 0, done.stderr


def test_the_family_prefix_is_the_prefix_the_release_workflow_tags_with() -> None:
    ledger = tomllib.loads(LEDGER.read_text("utf-8"))
    config = tomllib.loads((REPO / ".vibey-gh.toml").read_text("utf-8"))
    assert [f["tag_prefix"] for f in ledger["family"]] == [config["github_release"]["tag_prefix"]]


def test_every_entry_names_its_family_tag_and_a_full_commit() -> None:
    ledger = tomllib.loads(LEDGER.read_text("utf-8"))
    prefix = ledger["family"][0]["tag_prefix"]
    assert ledger["release"], "the ledger records no release"
    for release in ledger["release"]:
        assert release["tag"] == f"{prefix}{release['version']}"
        assert len(release["commit"]) == 40
        assert release["released"].utcoffset() is not None


def test_sync_records_every_release_tag_once_and_nothing_else(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "tag", "vibey-v1.0.0")
    _git(repo, "tag", "-a", "vibey-v1.1.0", "-m", "annotated")
    _git(repo, "tag", "krypton-nightly")
    _git(repo, "tag", "scrapped/vibey-v0.0.1")
    first = _run(repo, "sync")
    assert first.returncode == 0, first.stderr
    assert _entries(repo) == ["vibey-v1.0.0", "vibey-v1.1.0"]
    text = (repo / "docs" / "paper_releases.toml").read_text("utf-8")
    commit = _git(repo, "rev-parse", "HEAD")
    assert text.count(commit) == 2, "an annotated tag is recorded at its commit, not its tag object"
    again = _run(repo, "sync")
    assert again.returncode == 0 and "0 release(s) recorded" in again.stdout
    assert (repo / "docs" / "paper_releases.toml").read_text("utf-8") == text


def test_a_tag_deleted_after_sync_stays_recorded(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "tag", "vibey-v1.0.0")
    assert _run(repo, "sync").returncode == 0
    _git(repo, "tag", "-d", "vibey-v1.0.0")
    assert _run(repo, "sync").returncode == 0
    assert _entries(repo) == ["vibey-v1.0.0"]


def test_check_fails_loudly_when_the_release_branch_ships_an_unrecorded_version(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, version="1.0.0")
    done = _run(repo, "check")
    assert done.returncode == 1
    assert "vibey 1.0.0" in done.stderr and "origin/main" in done.stderr
    assert "paper_releases.py sync" in done.stderr
    _git(repo, "tag", "vibey-v1.0.0")
    _run(repo, "sync")
    assert _run(repo, "check").returncode == 0


def test_an_unreleased_version_never_fails_the_check(tmp_path: Path) -> None:
    """A feature branch that stages 2.0.0 is not held: only what the release branch ships counts."""
    repo = _repo(tmp_path, version="1.0.0")
    _git(repo, "tag", "vibey-v1.0.0")
    _run(repo, "sync")
    (repo / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "2.0.0"\n')
    _git(repo, "commit", "-q", "-am", "chore(release): stage 2.0.0")
    assert _run(repo, "check").returncode == 0


def test_check_says_so_when_the_release_branch_is_not_in_the_clone(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    done = _run(repo, "check")
    assert done.returncode == 0 and "not checked here" in done.stdout


def test_the_release_branch_is_read_from_the_repository_config(tmp_path: Path) -> None:
    repo = _repo(tmp_path, version="1.0.0")
    (repo / ".vibey-gh.toml").write_text('[branches]\nrelease = "stable"\n', encoding="utf-8")
    _git(repo, "update-ref", "refs/remotes/origin/stable", "HEAD")
    _git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    done = _run(repo, "check")
    assert done.returncode == 1 and "origin/stable" in done.stderr


def test_a_malformed_ledger_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    ledger = repo / "docs" / "paper_releases.toml"
    entry = (
        '\n[[release]]\npackage = "vibey"\nversion = "1.0.0"\ntag = "vibey-v1.0.0"\n'
        'commit = "{commit}"\nreleased = {released}\n'
    )
    good = "a" * 40
    cases = {
        "not a full 40-hex SHA": entry.format(
            commit="abc123", released="2026-08-16T03:55:58-04:00"
        ),
        "UTC offset": entry.format(commit=good, released="2026-08-16T03:55:58"),
        "recorded more than once": 2 * entry.format(commit=good, released="2026-08-16T03:55:58Z"),
    }
    for reason, body in cases.items():
        ledger.write_text(HEAD + body, encoding="utf-8")
        done = _run(repo, "check")
        assert done.returncode == 1 and reason in done.stderr, (reason, done.stderr)
    ledger.write_text(
        HEAD
        + entry.replace("vibey-v1.0.0", "other-v1.0.0").format(
            commit=good, released="2026-08-16T03:55:58Z"
        ),
        encoding="utf-8",
    )
    assert "is not vibey-v1.0.0" in _run(repo, "check").stderr
    ledger.write_text("[[family]\n", encoding="utf-8")
    assert "not valid TOML" in _run(repo, "check").stderr
    ledger.unlink()
    assert "does not exist" in _run(repo, "check").stderr
