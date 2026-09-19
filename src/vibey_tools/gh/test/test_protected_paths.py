# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[merge_train] protected_paths`: the merge train refuses what only a human may merge (#213).

The guard is pure and tested directly; the merge train's use of it is tested through
`judge`, and the listing it reads through `subprocess.run` monkeypatched to a recorder.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from vibey_gh import doctor, merge_train
from vibey_gh.config import GhConfig, PrAutomationConfig, load_config
from vibey_gh.interfaces.protected_paths_interface import ProtectedPathsInterface
from vibey_gh.protected_paths import CHANGED_PATHS_KEY, LISTED_FILES_KEY, ProtectedPathsGuard

GUARD: ProtectedPathsInterface = ProtectedPathsGuard()
PATTERNS = ("tests/domain/test_noloss*.py", "tests/live/*")


def listed(*paths: str, total: int | None = None) -> dict:
    """A pull request whose listing names `paths`, and whose GitHub count is `total`."""
    count = len(paths) if total is None else total
    return {CHANGED_PATHS_KEY: list(paths), LISTED_FILES_KEY: len(paths), "changedFiles": count}


# ------------------------------------------------------------------------------ matching


def test_a_pattern_matches_the_whole_root_relative_path_and_star_crosses_directories():
    paths = [
        "tests/live/harness/driver.py",
        "tests/domain/test_noloss.py",
        "tests/domain/test_noloss_reference.py",
        "tests/domain/test_ledger.py",
        "src/tests/live/elsewhere.py",
        "tests/live/harness/driver.py",
    ]
    assert GUARD.touched(PATTERNS, paths) == (
        "tests/domain/test_noloss.py",
        "tests/domain/test_noloss_reference.py",
        "tests/live/harness/driver.py",
    )


def test_matching_is_case_sensitive_on_every_platform():
    assert GUARD.touched(PATTERNS, ["Tests/live/x.py", "tests/domain/TEST_NOLOSS.py"]) == ()


# ------------------------------------------------------------------------------- listing


def test_a_merged_listing_names_every_file_and_a_renames_old_path():
    text = json.dumps(
        [
            {"filename": "a.py", "status": "modified"},
            {"filename": "b.py", "status": "renamed", "previous_filename": "tests/live/b.py"},
        ]
    )
    assert GUARD.parse_listing(text) == (("a.py", "b.py", "tests/live/b.py"), 2)


def test_concatenated_pages_from_an_older_gh_are_all_read():
    text = '[{"filename": "a.py"}]\n[{"filename": "b.py"}] \n'
    assert GUARD.parse_listing(text) == (("a.py", "b.py"), 2)


def test_an_empty_listing_names_nothing():
    assert GUARD.parse_listing("") == ((), 0)
    assert GUARD.parse_listing(" \n") == ((), 0)


@pytest.mark.parametrize(
    "text, error",
    [
        ('{"filename": "a.py"}', TypeError),
        ('[{"sha": "x"}]', TypeError),
        ('["a.py"]', TypeError),
        ('[{"filename": "a.py"}', ValueError),
    ],
)
def test_a_listing_that_is_not_the_files_endpoints_shape_raises(text, error):
    with pytest.raises(error):
        GUARD.parse_listing(text)


# ------------------------------------------------------------------------------- refusal


def test_nothing_is_refused_when_nothing_is_protected():
    assert GUARD.refusal({}, ()) is None


def test_a_listing_that_never_arrived_is_a_refusal_not_a_pass():
    reason = GUARD.refusal({"changedFiles": 3}, PATTERNS)
    assert reason is not None
    assert "could not be listed" in reason and "needs a human merge" in reason


@pytest.mark.parametrize(
    "pr",
    [
        listed("a.py", total=3001),
        {CHANGED_PATHS_KEY: ["a.py"], LISTED_FILES_KEY: 1},
        {CHANGED_PATHS_KEY: ["a.py"], "changedFiles": 1},
    ],
)
def test_a_listing_shorter_than_githubs_own_count_is_a_refusal(pr):
    """The REST listing stops at 3,000 files; a guard reading a truncated list would report
    the clean answer about files it never saw."""
    reason = GUARD.refusal(pr, PATTERNS)
    assert reason is not None
    assert "cannot be ruled out" in reason and "needs a human merge" in reason


def test_a_pull_request_touching_nothing_protected_is_not_refused():
    assert GUARD.refusal(listed("src/vibey/domain/noloss.py", "README.md"), PATTERNS) is None


def test_a_refusal_names_the_protected_paths_it_found():
    reason = GUARD.refusal(listed("README.md", "tests/live/a.py"), PATTERNS)
    assert reason == (
        "touches protected path(s) tests/live/a.py (merge_train.protected_paths)"
        " — needs a human merge"
    )


def test_a_long_refusal_names_three_and_counts_the_rest():
    touched = [f"tests/live/{n}.py" for n in range(5)]
    reason = GUARD.refusal(listed(*touched), PATTERNS)
    assert reason is not None
    assert "tests/live/0.py, tests/live/1.py, tests/live/2.py and 2 more" in reason


# ----------------------------------------------------------------------------- configuration


def test_protected_paths_default_to_none_and_load_as_a_tuple(tmp_path):
    assert load_config(tmp_path).protected_paths == ()
    (tmp_path / ".vibey-gh.toml").write_text(
        '[merge_train]\nprotected_paths = ["tests/live/*", ".github/CODEOWNERS"]\n'
    )
    assert load_config(tmp_path).protected_paths == ("tests/live/*", ".github/CODEOWNERS")


@pytest.mark.parametrize(
    "value, match",
    [
        ('"tests/live/*"', "list of strings"),
        ("[1]", "list of strings"),
        ('["/tests/live/*"]', "without a leading '/'"),
        ('["tests/live/*", "tests/live/*"]', "unique"),
        ('[" "]', "non-empty"),
    ],
)
def test_a_pattern_that_could_never_match_is_refused_at_load(tmp_path, value, match):
    """A bare string would be split into one-character globs, and a CODEOWNERS-style `/`
    anchor matches no listed path: either way the key would protect nothing, silently."""
    (tmp_path / ".vibey-gh.toml").write_text(f"[merge_train]\nprotected_paths = {value}\n")
    with pytest.raises(ValueError, match=match):
        load_config(tmp_path)


def test_doctor_knows_the_key(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text('[merge_train]\nprotected_paths = ["tests/*"]\n')
    assert not any("protected_paths" in f.message for f in doctor._check_unknown_keys(tmp_path))


# ------------------------------------------------------------------------------- the train


def cfg_for(root: Path, **kw) -> GhConfig:
    base: dict = dict(
        root=root,
        owner="owner",
        trusted_authors=("owner",),
        pr_automation=PrAutomationConfig(enabled=False),
        protected_paths=PATTERNS,
    )
    base.update(kw)
    return GhConfig(**base)


def ready_pr(**kw) -> dict:
    pr = dict(
        number=7,
        title="t",
        isDraft=False,
        mergeable="MERGEABLE",
        reviewDecision=None,
        statusCheckRollup=[{"status": "COMPLETED", "conclusion": "SUCCESS"}],
        author={"login": "owner"},
        baseRefName="develop",
        headRefName="feat/x",
        **listed("src/a.py"),
    )
    pr.update(kw)
    return pr


def test_an_otherwise_ready_pull_request_touching_a_protected_path_needs_a_human(tmp_path):
    """The whole point: green, trusted, mergeable -- and still not the train's to merge,
    because its `--admin` fallback would bypass the code-owner review (#213)."""
    cfg = cfg_for(tmp_path)
    assert merge_train.judge(ready_pr(), cfg).ready
    verdict = merge_train.judge(ready_pr(**listed("tests/domain/test_noloss.py")), cfg)
    assert not verdict.ready
    assert verdict.reason is not None and "needs a human merge" in verdict.reason
    assert not verdict.held_for_review and not verdict.restackable


def test_an_earlier_obstacle_keeps_its_own_reason(tmp_path):
    verdict = merge_train.judge(
        ready_pr(isDraft=True, **listed("tests/live/a.py")), cfg_for(tmp_path)
    )
    assert verdict.reason == "draft"


def test_a_promotion_is_not_held_for_paths_already_merged_under_review(tmp_path, monkeypatch):
    monkeypatch.setattr(merge_train.versioning, "owed_at", lambda cfg, base, head: (None, ""))
    promotion = ready_pr(baseRefName="main", headRefName="develop", **listed("tests/live/a.py"))
    assert merge_train.judge(promotion, cfg_for(tmp_path)).ready
    hotfix = ready_pr(baseRefName="main", headRefName="fix/x", **listed("tests/live/a.py"))
    assert not merge_train.judge(hotfix, cfg_for(tmp_path)).ready


def test_nothing_changes_for_a_repository_that_protects_nothing(tmp_path):
    pr = ready_pr()
    for key in (CHANGED_PATHS_KEY, LISTED_FILES_KEY, "changedFiles"):
        pr.pop(key)
    assert merge_train.judge(pr, cfg_for(tmp_path, protected_paths=())).ready


def _recording(monkeypatch, *, code: int = 0, out: str = "") -> list[list[str]]:
    calls: list[list[str]] = []

    def run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, code, out, "")

    def view(*_args):
        # What `gh pr view` answers: GitHub's count, never the listing the train adds.
        pr = ready_pr(statusCheckRollup=[{"name": "PR automation / gate"}], changedFiles=2)
        del pr[CHANGED_PATHS_KEY], pr[LISTED_FILES_KEY]
        return pr

    monkeypatch.setattr(merge_train.subprocess, "run", run)
    monkeypatch.setattr(merge_train, "_gh_json", view)
    return calls


def test_the_train_reads_every_page_of_the_listing_when_paths_are_protected(tmp_path, monkeypatch):
    out = json.dumps([{"filename": "tests/live/a.py"}, {"filename": "b.py"}])
    calls = _recording(monkeypatch, out=out)
    pr = merge_train.pull_request(7, cfg_for(tmp_path))
    assert calls == [["gh", "api", "--paginate", "repos/{owner}/{repo}/pulls/7/files?per_page=100"]]
    assert pr[CHANGED_PATHS_KEY] == ["tests/live/a.py", "b.py"]
    assert pr[LISTED_FILES_KEY] == 2


@pytest.mark.parametrize("code, out", [(1, ""), (0, "not json"), (0, '{"message": "x"}')])
def test_a_listing_that_fails_is_left_absent_so_the_judge_refuses(tmp_path, monkeypatch, code, out):
    _recording(monkeypatch, code=code, out=out)
    pr = merge_train.pull_request(7, cfg_for(tmp_path))
    assert CHANGED_PATHS_KEY not in pr
    verdict = merge_train.judge(pr, cfg_for(tmp_path))
    assert verdict.reason is not None and "could not be listed" in verdict.reason


def test_no_listing_is_fetched_when_nothing_is_protected(tmp_path, monkeypatch):
    calls = _recording(monkeypatch)
    merge_train.pull_request(7, cfg_for(tmp_path, protected_paths=()))
    merge_train.pull_request(7)
    assert calls == []


def test_open_pull_requests_hands_the_configuration_to_every_lookup(tmp_path, monkeypatch):
    seen: list[tuple[int, GhConfig | None]] = []
    monkeypatch.setattr(merge_train, "_gh_json", lambda *args: [{"number": 3}])
    monkeypatch.setattr(
        merge_train,
        "pull_request",
        lambda number, cfg=None: seen.append((number, cfg)) or {"number": number},
    )
    cfg = cfg_for(tmp_path)
    merge_train.open_pull_requests(cfg)
    merge_train.open_pull_requests(cfg, number=9)
    assert seen == [(3, cfg), (9, cfg)]
