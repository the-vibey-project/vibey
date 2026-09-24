# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Promotion: the half of the flow that used to be a hand-written workflow per repository.

Driven against a real bare repository over file:// and a fake `gh` on PATH, because the
things that go wrong here — comparing by commit count instead of content, promoting
without a version bump, merging before the checks land — are all in the interaction, not
in any single function.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from vibey_gh import promote as promote_mod
from vibey_gh.config import GhConfig


def git(cwd: Path, *a: str) -> str:
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    """A bare origin plus a clone with develop and main at the same commit."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)

    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "main", ".")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    (work / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "1.0.0"\n')
    (work / "content").mkdir()
    (work / "content" / "a.md").write_text("a\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "origin", "main")
    git(work, "push", "-q", "origin", "main:develop")
    git(work, "fetch", "-q", "origin")
    monkeypatch.chdir(work)
    return work


def cfg_for(root: Path) -> GhConfig:
    return GhConfig(
        root=root,
        version_files=("pyproject.toml",),
        content_paths=("content/",),
        code_paths=("src/",),
        integration_branch="develop",
        release_branch="main",
    )


@pytest.fixture
def fake_gh(tmp_path: Path, monkeypatch) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(f"""#!/usr/bin/env python3
import json, pathlib, sys
here = pathlib.Path({str(bin_dir)!r})
with (here / "calls.txt").open("a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\\n")
# One JSON array per call as well: a multi-line --body splits calls.txt across lines.
with (here / "argv.jsonl").open("a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
answers = json.loads((here / "answers.json").read_text())
for key, entry in answers.items():
    if " ".join(sys.argv[1:]).startswith(key):
        sys.stdout.write(entry.get("out", ""))
        sys.stderr.write(entry.get("err", ""))
        raise SystemExit(entry.get("code", 0))
sys.stderr.write("no scripted answer\\n")
raise SystemExit(3)
""")
    gh.chmod(0o755)
    (bin_dir / "answers.json").write_text("{}")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


def script(bin_dir: Path, answers: dict) -> None:
    (bin_dir / "answers.json").write_text(json.dumps(answers))


def calls(bin_dir: Path) -> list[str]:
    path = bin_dir / "calls.txt"
    return path.read_text().splitlines() if path.exists() else []


def argvs(bin_dir: Path, *prefix: str) -> list[list[str]]:
    """Every `gh` call whose argv starts with `prefix`, each intact as one list."""
    path = bin_dir / "argv.jsonl"
    every = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return [argv for argv in every if argv[: len(prefix)] == list(prefix)]


def flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def advance_develop(work: Path, message: str = "new content") -> None:
    git(work, "checkout", "-qB", "develop", "origin/develop")
    (work / "content" / "b.md").write_text(message + "\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", message)
    git(work, "push", "-q", "origin", "develop")
    git(work, "fetch", "-q", "origin")


# ── nothing to do ──────────────────────────────────────────────────────────


def test_the_release_commit_is_itself_a_conventional_commit():
    """This subject does not stay on the release branch.

    Any topic branch that later merges the integration branch in pulls it into its own
    commit range, where the provenance gate reads it like any other commit. `Release
    1.23.0` blocked a pull request exactly that way, and the repair could not fix it by
    editing files because the problem was history rather than content.
    """
    from vibey_gh.fingerprints import conventional_subject
    from vibey_gh.promote import promote as _promote

    source = Path(_promote.__code__.co_filename).read_text(encoding="utf-8")
    assert "chore(release): " in source
    assert '"Release {' not in source and 'f"Release ' not in source
    for version in ("1.23.0", "2.0.0", "0.1.0.dev3"):
        assert conventional_subject(f"chore(release): {version}")


def test_identical_trees_promote_nothing(project, fake_gh):
    result = promote_mod.promote(cfg_for(project), wait=True)
    assert result.pull_request is None
    assert "nothing to promote" in " ".join(result.notes)
    assert not calls(fake_gh)  # and it does not even talk to GitHub


def test_a_rewritten_history_with_the_same_tree_is_still_nothing(project, fake_gh):
    """The case a commit count gets wrong: rebase-merging leaves divergent histories."""
    git(project, "checkout", "-qB", "develop", "origin/develop")
    git(project, "commit", "-q", "--allow-empty", "-m", "rewritten copy")
    git(project, "push", "-q", "origin", "develop")
    git(project, "fetch", "-q", "origin")
    assert git(project, "rev-parse", "origin/develop") != git(project, "rev-parse", "origin/main")

    result = promote_mod.promote(cfg_for(project), wait=True)
    assert "nothing to promote" in " ".join(result.notes)


# ── the happy path ─────────────────────────────────────────────────────────


def test_a_content_change_bumps_opens_waits_and_merges(project, fake_gh):
    advance_develop(project)
    script(
        fake_gh,
        {
            "pr list": {"out": "\n"},
            "pr create": {"out": "https://github.com/o/r/pull/42\n"},
            "pr checks 42": {},
            "pr merge 42 --rebase": {},
        },
    )

    result = promote_mod.promote(cfg_for(project), wait=True)

    assert result.bumped == "1.1.0"  # content changed -> minor
    assert result.version == "1.1.0"
    assert result.pull_request == 42
    assert result.merged is True and result.bypassed is False
    # the bump was pushed, so the promotion actually publishes something
    assert 'version = "1.1.0"' in git(project, "show", "origin/develop:pyproject.toml")
    joined = " ".join(calls(fake_gh))
    assert "pr checks 42 --watch" in joined  # it waited


def test_an_existing_pull_request_is_reused(project, fake_gh):
    advance_develop(project)
    script(
        fake_gh,
        {
            "pr list": {"out": "7\n"},
            "pr checks 7": {},
            "pr merge 7 --rebase": {},
        },
    )
    result = promote_mod.promote(cfg_for(project), wait=True)
    assert result.pull_request == 7
    assert "reusing #7" in " ".join(result.notes)
    assert not [c for c in calls(fake_gh) if c.startswith("pr create")]


_REFUSED = "GraphQL: Pull request is not mergeable: REVIEW_REQUIRED"


def test_a_refused_promotion_waits_for_a_person_and_never_tries_admin(project, fake_gh):
    """ADR-0053 / sub-doctrine 12.d: a promotion runs unattended, so a refusal is the gate
    working. It is reported in GitHub's own words and nothing routes around it."""
    advance_develop(project)
    script(
        fake_gh,
        {
            "pr list": {"out": "7\n"},
            "pr checks 7": {},
            # Would succeed if asked -- which is exactly what must not happen by default.
            "pr merge 7 --rebase --admin": {},
            "pr merge 7 --rebase": {"err": _REFUSED + "\n", "code": 1},
        },
    )
    result = promote_mod.promote(cfg_for(project), wait=True)
    assert result.merged is False and result.bypassed is False
    assert not [c for c in calls(fake_gh) if c.endswith("--admin")]
    assert f"#7 needs a human merge: {_REFUSED}" in result.notes


def test_the_admin_fallback_is_a_persons_per_run_choice(project, fake_gh):
    advance_develop(project)
    script(
        fake_gh,
        {
            "pr list": {"out": "7\n"},
            "pr checks 7": {},
            "pr merge 7 --rebase --admin": {},
            "pr merge 7 --rebase": {"err": _REFUSED + "\n", "code": 1},
        },
    )
    result = promote_mod.promote(cfg_for(project), wait=True, admin_fallback=True)
    assert result.merged is True and result.bypassed is True
    assert calls(fake_gh)[-1].endswith("--admin")


def test_a_merge_nothing_can_satisfy_leaves_the_pull_request_open(project, fake_gh):
    advance_develop(project)
    script(fake_gh, {"pr list": {"out": "7\n"}, "pr checks 7": {}})
    result = promote_mod.promote(cfg_for(project), wait=True, admin_fallback=True)
    assert result.merged is False and result.bypassed is True
    assert "#7 needs a human merge: no scripted answer" in result.notes


# ── the guards ─────────────────────────────────────────────────────────────


def test_failing_checks_stop_the_merge(project, fake_gh):
    advance_develop(project)
    script(
        fake_gh,
        {
            "pr list": {"out": "7\n"},
            "pr checks 7": {"code": 1},
        },
    )
    result = promote_mod.promote(cfg_for(project), wait=True)
    assert result.merged is False
    assert "checks did not pass" in " ".join(result.notes)
    assert not [c for c in calls(fake_gh) if c.startswith("pr merge")]


def test_event_driven_mode_does_not_wait_or_merge(project, fake_gh):
    advance_develop(project)
    script(fake_gh, {"pr list": {"out": "7\n"}, "pr merge 7 --rebase": {}})
    result = promote_mod.promote(cfg_for(project), wait=False)
    assert result.merged is False
    assert not [c for c in calls(fake_gh) if c.startswith("pr checks")]
    assert not [c for c in calls(fake_gh) if c.startswith("pr merge")]
    assert "event-driven" in " ".join(result.notes)


def test_a_bump_that_cannot_be_pushed_is_fatal(project, fake_gh):
    """An unpushed bump means the promotion publishes nothing — silently, without this."""
    advance_develop(project)
    origin = project.parent / "origin.git" / "hooks"
    origin.mkdir(exist_ok=True)
    (origin / "pre-receive").write_text("#!/bin/sh\nexit 1\n")
    (origin / "pre-receive").chmod(0o755)

    with pytest.raises(RuntimeError, match="publish nothing"):
        promote_mod.promote(cfg_for(project))


def test_a_pull_request_that_cannot_be_opened_is_fatal(project, fake_gh):
    advance_develop(project)
    script(fake_gh, {"pr list": {"out": "\n"}})  # create has no scripted answer
    with pytest.raises(RuntimeError, match="could not open"):
        promote_mod.promote(cfg_for(project))


# ── dry run ────────────────────────────────────────────────────────────────


def test_a_dry_run_bumps_nothing_and_opens_nothing(project, fake_gh):
    advance_develop(project)
    result = promote_mod.promote(cfg_for(project), dry_run=True)

    assert result.bumped == "1.1.0"
    assert "would bump to 1.1.0" in " ".join(result.notes)
    assert result.pull_request is None
    assert 'version = "1.0.0"' in git(project, "show", "origin/develop:pyproject.toml")
    assert not [c for c in calls(fake_gh) if c.startswith("pr create")]


def test_a_promotion_with_nothing_to_bump_still_proceeds(project, fake_gh):
    """Docs and CI reach no installed user; `none` is a legitimate answer."""
    git(project, "checkout", "-qB", "develop", "origin/develop")
    (project / "README.md").write_text("docs\n")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "docs only")
    git(project, "push", "-q", "origin", "develop")
    git(project, "fetch", "-q", "origin")

    script(fake_gh, {"pr list": {"out": "7\n"}, "pr checks 7": {}, "pr merge 7 --rebase": {}})
    result = promote_mod.promote(cfg_for(project), wait=True)

    assert result.bumped is None
    assert result.merged is True
    assert "none reach an installed user" in " ".join(result.notes)


def test_a_deliberate_bump_already_in_place_is_not_doubled(project, fake_gh):
    advance_develop(project)
    git(project, "checkout", "-qB", "develop", "origin/develop")
    (project / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "2.0.0"\n')
    git(project, "add", "-A")
    git(project, "commit", "-qm", "bump by hand")
    git(project, "push", "-q", "origin", "develop")
    git(project, "fetch", "-q", "origin")

    script(fake_gh, {"pr list": {"out": "7\n"}, "pr checks 7": {}, "pr merge 7 --rebase": {}})
    result = promote_mod.promote(cfg_for(project))
    assert result.bumped is None
    assert result.version == "2.0.0"


# ── a reused pull request says what it proposes now (#235) ─────────────────

# The body every promotion carried before #235, word for word: no record of its version.
STALE_BODY = (
    "Promotion opened by `vibey-gh promote`.\n\n"
    "5 file(s) differ from `main`. The package version is `1.0.0` — merging publishes it, "
    "and an upload skips a version the index already holds, so a promotion nobody bumped "
    "publishes nothing.\n\n"
    "Merged with `--rebase`, which is the only method consistent with a linear-history rule."
)
PROJECTS_CLASSIC = (
    "GraphQL: Projects (classic) is being deprecated in favor of the new Projects "
    "experience, see: https://github.blog/changelog/2024-05-23-sunset-notice-projects-classic/"
    ". (repository.pullRequest.projectCards)\n"
)
PATCH_ENDPOINT = "repos/{owner}/{repo}/pulls/7"


def view(title: str, body: str) -> dict:
    return {"out": json.dumps({"title": title, "body": body})}


def reuse(title: str = "chore(release): 1.0.0", body: str = STALE_BODY, **more: dict) -> dict:
    """Answers for a run that finds #7 open, reads it, and edits it."""
    return {"pr list": {"out": "7\n"}, "pr view 7": view(title, body), "pr edit 7": {}, **more}


def docs_only(work: Path) -> None:
    git(work, "checkout", "-qB", "develop", "origin/develop")
    (work / "README.md").write_text("docs\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "docs only")
    git(work, "push", "-q", "origin", "develop")
    git(work, "fetch", "-q", "origin")


def test_the_promotion_pull_request_implements_its_seam(tmp_path):
    from vibey_gh.interfaces.promotion_pull_request_interface import (
        PromotionPullRequestInterface,
    )

    seam = promote_mod.PromotionPullRequest(cfg_for(tmp_path))
    assert isinstance(seam, PromotionPullRequestInterface)


def test_a_reused_pull_request_is_retitled_and_rewritten(project, fake_gh):
    """The reuse path recomputed everything and wrote none of it back."""
    advance_develop(project)
    script(fake_gh, reuse())

    result = promote_mod.promote(cfg_for(project))

    assert result.previous == "1.0.0"  # from the title: the old body carries no record
    assert result.released == "1.0.0"
    (edit,) = argvs(fake_gh, "pr", "edit", "7")
    assert flag(edit, "--title") == "chore(release): 1.1.0"
    body = flag(edit, "--body")
    record = '<!-- vibey-gh-promotion:{"opened":"1.0.0","version":"1.1.0"} -->\n'
    assert body.startswith(record)
    assert "1 file(s) differ from `main`" in body
    assert "Merging publishes `1.1.0` (`main` is at `1.0.0`)." in body
    changed = "Opened as `1.0.0`; now `1.1.0` (version derivation: packaged content changed)."
    assert changed in body
    assert "publishes nothing" not in body
    refreshed = "reusing #7; refreshed its title and body (opened as 1.0.0, now 1.1.0)"
    assert refreshed in result.notes
    assert not argvs(fake_gh, "pr", "create")


def test_the_body_record_outranks_the_title(project, fake_gh):
    advance_develop(project)
    recorded = '<!-- vibey-gh-promotion:{"opened":"0.9.0","version":"1.0.0"} -->\n## x\n'
    script(fake_gh, reuse(title="renamed by a human", body=recorded))

    result = promote_mod.promote(cfg_for(project))

    assert result.previous == "0.9.0"
    body = flag(argvs(fake_gh, "pr", "edit", "7")[0], "--body")
    assert '{"opened":"0.9.0","version":"1.1.0"}' in body
    assert "Opened as `0.9.0`; now `1.1.0`" in body


def test_a_title_in_no_known_shape_is_unknown_not_guessed(project, fake_gh):
    advance_develop(project)
    script(fake_gh, reuse(title="Promote develop to main", body="hand-written"))

    result = promote_mod.promote(cfg_for(project))

    assert result.previous is None
    (edit,) = argvs(fake_gh, "pr", "edit", "7")
    assert flag(edit, "--title") == "chore(release): 1.1.0"
    body = flag(edit, "--body")
    assert '{"opened":"1.1.0","version":"1.1.0"}' in body
    assert "Opened as" not in body
    assert "reusing #7; refreshed its title and body" in result.notes


@pytest.mark.parametrize(
    ("answer", "detail"),
    [
        ({"code": 1, "err": "HTTP 502: Bad Gateway\n"}, "HTTP 502: Bad Gateway"),
        ({"code": 1}, "gh pr view exited 1"),
        ({"out": "not json"}, "did not return a title and body"),
        ({"out": "[]"}, "did not return a title and body"),
    ],
)
def test_a_pull_request_that_cannot_be_read_is_still_refreshed(project, fake_gh, answer, detail):
    """Not knowing what it says now is no reason to leave it saying it."""
    advance_develop(project)
    script(fake_gh, {**reuse(), "pr view 7": answer})

    result = promote_mod.promote(cfg_for(project))

    assert result.previous is None
    (edit,) = argvs(fake_gh, "pr", "edit", "7")
    assert flag(edit, "--title") == "chore(release): 1.1.0"
    unread = [note for note in result.notes if note.startswith("could not read #7")]
    assert unread and detail in unread[0]
    assert "reusing #7; refreshed its title and body" in result.notes


@pytest.mark.parametrize(
    ("answer", "detail"),
    [
        ({"code": 1, "err": "HTTP 403: Resource not accessible\n"}, "HTTP 403: Resource not"),
        ({"code": 1}, "gh pr edit exited 1"),
    ],
)
def test_an_edit_that_fails_is_a_note_not_a_crash(project, fake_gh, answer, detail):
    advance_develop(project)
    script(fake_gh, {**reuse(), "pr edit 7": answer})

    result = promote_mod.promote(cfg_for(project))

    assert result.pull_request == 7
    failed = [note for note in result.notes if note.startswith("reusing #7; could not refresh")]
    assert failed and detail in failed[0]
    assert "event-driven" in " ".join(result.notes)  # and the promotion carried on
    assert not argvs(fake_gh, "api")  # only the Projects (classic) refusal earns the fallback


def test_the_projects_classic_refusal_falls_back_to_rest(project, fake_gh):
    advance_develop(project)
    script(
        fake_gh,
        {**reuse(), "pr edit 7": {"code": 1, "err": PROJECTS_CLASSIC}, f"api {PATCH_ENDPOINT}": {}},
    )

    result = promote_mod.promote(cfg_for(project))

    (edit,) = argvs(fake_gh, "pr", "edit", "7")
    (patch,) = argvs(fake_gh, "api", PATCH_ENDPOINT)
    title, body = flag(edit, "--title"), flag(edit, "--body")
    assert patch[2:] == ["--method", "PATCH", "-f", f"title={title}", "-f", f"body={body}"]
    refreshed = "reusing #7; refreshed its title and body (opened as 1.0.0, now 1.1.0)"
    assert refreshed in result.notes


def test_a_rest_fallback_that_fails_too_names_both_refusals(project, fake_gh):
    advance_develop(project)
    script(
        fake_gh,
        {
            **reuse(),
            "pr edit 7": {"code": 1, "err": PROJECTS_CLASSIC},
            f"api {PATCH_ENDPOINT}": {"code": 1, "err": "HTTP 404: Not Found\n"},
        },
    )

    result = promote_mod.promote(cfg_for(project))

    failed = [note for note in result.notes if note.startswith("reusing #7; could not refresh")]
    assert failed and "Projects (classic)" in failed[0]
    assert "the REST fallback failed too — HTTP 404: Not Found" in failed[0]


def test_words_already_current_are_not_sent_again(project, fake_gh):
    """Runs converge: once the pull request says what the derivation says, nothing is sent."""
    advance_develop(project)
    script(fake_gh, reuse())
    promote_mod.promote(cfg_for(project))
    first = argvs(fake_gh, "pr", "edit", "7")[-1]

    # The second run sees the bump the first one pushed, so the words move once more.
    script(fake_gh, reuse(title=flag(first, "--title"), body=flag(first, "--body")))
    again = promote_mod.promote(cfg_for(project))
    second = argvs(fake_gh, "pr", "edit", "7")[-1]
    body = flag(second, "--body")
    assert "2 file(s) differ from `main`" in body
    assert again.previous == "1.0.0"  # carried by the record, not forgotten after one run
    assert "Opened as `1.0.0`; now `1.1.0` (version derivation: already at 1.1.0" in body

    # A forge that hands the body back with CRLF line ends and no final newline has not
    # changed it.
    crlf = body.replace("\n", "\r\n").strip()
    script(fake_gh, reuse(title=flag(second, "--title"), body=crlf))
    sent = len(argvs(fake_gh, "pr", "edit"))
    settled = promote_mod.promote(cfg_for(project))

    assert len(argvs(fake_gh, "pr", "edit")) == sent
    assert "reusing #7; its title and body are already current" in settled.notes


@pytest.mark.parametrize("reused", [False, True])
def test_publishes_nothing_is_said_only_of_an_unbumped_promotion(project, fake_gh, reused):
    docs_only(project)
    listed = "7\n" if reused else "\n"
    script(
        fake_gh,
        {**reuse(), "pr list": {"out": listed}, "pr create": {"out": "https://x/pull/7\n"}},
    )

    result = promote_mod.promote(cfg_for(project))

    assert result.bumped is None and result.released == result.version == "1.0.0"
    (sent,) = argvs(fake_gh, "pr", "edit" if reused else "create")
    assert flag(sent, "--title") == "chore(release): 1.0.0"
    body = flag(sent, "--body")
    assert "the same as `main`'s" in body and "publishes nothing" in body
    assert "Merging publishes" not in body and "Opened as" not in body


@pytest.mark.parametrize("reused", [False, True])
def test_a_bumped_promotion_says_what_merging_publishes(project, fake_gh, reused):
    advance_develop(project)
    listed = "7\n" if reused else "\n"
    script(
        fake_gh,
        {**reuse(), "pr list": {"out": listed}, "pr create": {"out": "https://x/pull/7\n"}},
    )

    promote_mod.promote(cfg_for(project))

    (sent,) = argvs(fake_gh, "pr", "edit" if reused else "create")
    assert flag(sent, "--title") == "chore(release): 1.1.0"
    body = flag(sent, "--body")
    assert "Merging publishes `1.1.0` (`main` is at `1.0.0`)." in body
    assert "publishes nothing" not in body


def test_an_unreadable_release_version_is_neither_promised_nor_denied(project, fake_gh):
    git(project, "checkout", "-q", "main")
    (project / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    git(project, "commit", "-qam", "no version on the release branch")
    git(project, "push", "-q", "origin", "main")
    git(project, "fetch", "-q", "origin")
    advance_develop(project)
    script(fake_gh, {"pr list": {"out": "\n"}, "pr create": {"out": "https://x/pull/9\n"}})

    result = promote_mod.promote(cfg_for(project))

    assert result.released is None and result.version == "1.0.0"
    body = flag(argvs(fake_gh, "pr", "create")[0], "--body")
    assert "the version on `main` could not be read" in body
    assert "publishes nothing" not in body and "Merging publishes" not in body


def test_a_changed_version_with_no_stated_reason_still_says_it_changed(tmp_path):
    seam = promote_mod.PromotionPullRequest(cfg_for(tmp_path))
    result = promote_mod.Promotion(
        changed_files=3, version="2.0.0", released="1.0.0", previous="1.1.0"
    )
    assert "Opened as `1.1.0`; now `2.0.0`.\n" in seam.body(result)


@pytest.mark.parametrize(
    ("title", "body", "expected"),
    [
        ("x", '<!-- vibey-gh-promotion:{"opened":"0.8.0","version":"1.0.0"} -->', "0.8.0"),
        ("x", '<!-- vibey-gh-promotion:{"version":"1.0.0"} -->', "1.0.0"),
        ("chore(release): 0.7.0", '<!-- vibey-gh-promotion:{"opened":5,"version":""} -->', "0.7.0"),
        ("chore(release): 0.7.0", '<!-- vibey-gh-promotion:{"opened":"a b"} -->', "0.7.0"),
        ("chore(release): 0.7.0", "<!-- vibey-gh-promotion:{not json} -->", "0.7.0"),
        ("  chore(release): 0.7.0\n", "no record at all", "0.7.0"),
        ("chore(release): 0.7.0 and more", "", None),
        ("chore(deps): 0.7.0", "", None),
    ],
)
def test_the_version_a_pull_request_was_opened_at(tmp_path, title, body, expected):
    seam = promote_mod.PromotionPullRequest(cfg_for(tmp_path))
    assert seam.recorded_version(title, body) == expected
