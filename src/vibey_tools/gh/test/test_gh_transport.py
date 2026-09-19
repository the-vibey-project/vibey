# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `gh` transport, and the proof that moving `github_state` onto it changed nothing.

Everything here runs a real process: the `fake_gh` on PATH from `conftest.py`, which records
the argv it received as a list and the directory it ran in. A patched `subprocess.run`
could only confirm that the code called what the code calls.

The proof is before/after. `Before` holds the runners exactly as they stood at 4e9adf18,
and each comparison drives the old code and the new against the same scripted `gh`, then
requires the same outcome, the same argv, the same working directory and the same bytes
in `calls.txt`. A scenario whose `gh` was never reached would compare equal on both sides
and prove nothing, so every scenario also pins what it expects to have seen.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import github_state
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface

MARKER = "vibey-gh-transport-test"
PATTERN = github_state.marker_pattern(MARKER)
# A body with the things a joined command line hides: spaces, a newline, a quote.
BODY = github_state.render_body(MARKER, {"n": 1}, "State", 'two words\nand "a quote"')
MUTATION = (
    "mutation($id:ID!,$body:String!){updateIssueComment(input:{id:$id,body:$body})"
    "{issueComment{id}}}"
)


class Before:
    """The runners as they stood at 4e9adf18, gathered into one class and otherwise verbatim.

    `gh_json`, `repository` and `upsert_comment` are `github_state`'s; the other three are
    the private runners `probe` and `survey` are extracted from — `promote._gh` (given the
    root it read from `cfg.root`), `merge_train._gh` and `tidy._gh_json`. Kept as copies,
    not imported, so this proof still says what it says after those modules move on.
    """

    @staticmethod
    def gh_json(*args: str) -> Any:
        run = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
        if run.returncode:
            raise RuntimeError(f"gh {' '.join(args)}: {run.stderr.strip()}")
        return json.loads(run.stdout or "null")

    @classmethod
    def repository(cls) -> str:
        name = os.environ.get("GH_REPO")
        if not name:
            name = str(cls.gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"])
        return name

    @classmethod
    def upsert_comment(
        cls,
        number: int,
        body: str,
        comments: Sequence[dict[str, Any]],
        pattern: re.Pattern[str],
        *,
        subject: str = "pr",
        error: str = "could not persist automation state",
    ) -> None:
        repository_name = cls.repository()
        existing: dict[str, Any] | None = None
        for comment in reversed(comments):
            if pattern.search(str(comment.get("body", ""))):
                existing = comment
                break
        if existing is None:
            run = subprocess.run(
                ["gh", subject, "comment", str(number), "--repo", repository_name, "--body", body],
                capture_output=True,
                text=True,
                check=False,
            )
        elif existing.get("databaseId") is not None:
            comment_id = existing["databaseId"]
            run = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{repository_name}/issues/comments/{comment_id}",
                    "--method",
                    "PATCH",
                    "--field",
                    f"body={body}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            comment_id = existing.get("id")
            if not comment_id:
                raise RuntimeError(f"{error}: comment has no ID")
            mutation = (
                "mutation($id:ID!,$body:String!){updateIssueComment(input:{id:$id,body:$body})"
                "{issueComment{id}}}"
            )
            run = subprocess.run(
                [
                    "gh",
                    "api",
                    "graphql",
                    "--field",
                    f"query={mutation}",
                    "--field",
                    f"id={comment_id}",
                    "--field",
                    f"body={body}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        if run.returncode:
            raise RuntimeError(f"{error}: {run.stderr.strip()}")

    @staticmethod
    def promote_gh(root: Path, *args: str) -> tuple[bool, str]:
        r = subprocess.run(["gh", *args], cwd=root, capture_output=True, text=True, check=False)
        return r.returncode == 0, (r.stdout or "").strip()

    @staticmethod
    def merge_train_gh(*args: str) -> tuple[bool, str]:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")

    @staticmethod
    def tidy_gh_json(root: Path, *args: str) -> tuple[list | dict, str]:
        label = " ".join(("gh", *args[:2]))
        try:
            run = subprocess.run(
                ["gh", *args], cwd=root, capture_output=True, text=True, check=False
            )
        except FileNotFoundError:
            return [], "the GitHub CLI (`gh`) is not installed"
        if run.returncode != 0:
            detail = (run.stderr or run.stdout).strip().splitlines()
            return [], f"`{label}` failed: {detail[-1] if detail else 'no output'}"
        try:
            value = json.loads(run.stdout)
        except json.JSONDecodeError:
            return [], f"`{label}` returned output that is not JSON"
        if isinstance(value, (list, dict)):
            return value, ""
        return [], f"`{label}` returned JSON that is neither a list nor an object"


class Witness:
    """Runs one action against the fake and keeps everything an observer could see of it."""

    def __init__(self, fake: Any) -> None:
        self.fake = fake

    def observe(self, action: Callable[[], Any]) -> dict[str, Any]:
        try:
            outcome: tuple[Any, ...] = ("returned", action())
        # Every exception a runner here can raise: a non-zero exit (RuntimeError), output
        # that is not JSON (ValueError), a missing executable (OSError). It IS the outcome.
        except (RuntimeError, ValueError, OSError) as exc:
            outcome = ("raised", type(exc).__name__, str(exc))
        seen = {
            "outcome": outcome,
            "invocations": self.fake.invocations(),
            "calls": self.fake.calls(),
        }
        self.fake.forget()
        return seen

    def compare(self, before: Callable[[], Any], after: Callable[[], Any]) -> dict[str, Any]:
        """Both sides' observations, required equal; returns the shared one to pin."""
        old, new = self.observe(before), self.observe(after)
        assert new == old
        return new


# The fixtures and `key` are module-level (vibey ADR-0016): pytest resolves fixtures by name
# at module scope, and `key` is the one-word spelling of a scripted answer that every
# scenario table below repeats, which a method would only lengthen.
@pytest.fixture
def witness(fake_gh) -> Witness:
    return Witness(fake_gh)


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch) -> Path:
    """Run from a directory of the test's own, so 'where it ran' is a fact worth comparing."""
    path = tmp_path / "work"
    path.mkdir()
    monkeypatch.chdir(path)
    return path.resolve()


def key(*argv: str) -> str:
    return " ".join(argv)


# ------------------------------------------------------------------- the contract


def test_the_transport_is_the_declared_seam_and_the_one_github_state_rides_on():
    assert isinstance(GhTransport(), GhTransportInterface)
    assert isinstance(github_state._transport, GhTransport)
    assert GhTransport().executable == "gh"


# ------------------------------------------------------------------------- run


def test_run_prefixes_the_executable_and_never_raises_on_the_exit(fake_gh, workdir):
    fake_gh.script({key("pr", "view", "7"): {"out": "o", "err": "e", "code": 4}})
    run = GhTransport().run(["pr", "view", "7"])
    assert (run.args, run.returncode, run.stdout, run.stderr) == (
        ["gh", "pr", "view", "7"],
        4,
        "o",
        "e",
    )
    assert fake_gh.invocations() == [
        {"argv": ["pr", "view", "7"], "cwd": str(workdir), "stdin": None}
    ]


@pytest.mark.parametrize("as_text", [False, True])
def test_run_runs_where_it_is_told(fake_gh, workdir, tmp_path, as_text):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    fake_gh.script({key("pr", "list"): {}})
    GhTransport().run(["pr", "list"], cwd=str(elsewhere) if as_text else elsewhere)
    assert [call["cwd"] for call in fake_gh.invocations()] == [str(elsewhere.resolve())]


def test_run_hands_the_process_its_standard_input(fake_gh, workdir):
    body = json.dumps({"name": "develop", "rules": []})
    fake_gh.script({key("api", "x", "--input", "-"): {"read_stdin": True}})
    assert GhTransport().run(["api", "x", "--input", "-"], stdin=body).returncode == 0
    assert fake_gh.invocations()[0]["stdin"] == body


# ------------------------------------------------------------------------ json


def test_json_decodes_and_reads_nothing_as_null(fake_gh, workdir):
    fake_gh.script({key("a"): {"out": '{"k": [1]}'}, key("b"): {"out": ""}})
    assert GhTransport().json(["a"]) == {"k": [1]}
    assert GhTransport().json(["b"]) is None


def test_json_raises_with_the_command_and_its_stderr(fake_gh, workdir):
    fake_gh.script({key("api", "x"): {"err": "  HTTP 404  \n", "code": 1}})
    with pytest.raises(RuntimeError) as raised:
        GhTransport().json(["api", "x"])
    assert str(raised.value) == "gh api x: HTTP 404"


def test_json_lets_output_that_is_not_json_through_as_itself(fake_gh, workdir):
    fake_gh.script({key("a"): {"out": "not json"}})
    with pytest.raises(json.JSONDecodeError):
        GhTransport().json(["a"])


# ----------------------------------------------------------------------- probe


def test_probe_reports_the_exit_and_a_stripped_stdout_by_default(fake_gh, workdir):
    fake_gh.script({key("pr", "list"): {"out": "  7\n", "err": "warning"}})
    assert GhTransport().probe(["pr", "list"]) == (True, "7")


def test_probe_can_keep_both_streams_verbatim(fake_gh, workdir):
    fake_gh.script({key("pr", "edit"): {"out": " out\n", "err": "err\n", "code": 1}})
    assert GhTransport().probe(["pr", "edit"], strip=False, with_stderr=True) == (
        False,
        " out\nerr\n",
    )


# ---------------------------------------------------------------------- survey


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ({"out": "[1, 2]"}, ([1, 2], "")),
        ({"out": '{"a": 1}'}, ({"a": 1}, "")),
        ({"err": "first\nlast\n", "code": 1}, ([], "`gh api repos` failed: last")),
        ({"out": "only stdout\n", "code": 1}, ([], "`gh api repos` failed: only stdout")),
        ({"code": 1}, ([], "`gh api repos` failed: no output")),
        ({"out": "<html>"}, ([], "`gh api repos` returned output that is not JSON")),
        ({"out": "3"}, ([], "`gh api repos` returned JSON that is neither a list nor an object")),
    ],
)
def test_survey_says_which_thing_happened(fake_gh, workdir, answer, expected):
    fake_gh.script({key("api", "repos", "--paginate"): answer})
    assert GhTransport().survey(["api", "repos", "--paginate"]) == expected


def test_survey_says_the_client_is_missing_rather_than_raising(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert GhTransport().survey(["api", "x"]) == (
        [],
        "the GitHub CLI (`gh`) is not installed",
    )


# ------------------------------------------- before/after: each shape vs its twin

SHAPE_ANSWERS = [
    {"out": '{"number": 7}'},
    {"out": "[1, 2]\n"},
    {"out": ""},
    {"out": "  padded  \n", "err": "noise\n"},
    {"out": "<html>"},
    {"out": "3"},
    {"err": "gh: Not Found (HTTP 404)\n", "code": 1},
    {"out": "partial\n", "code": 1},
    {"code": 2},
]


@pytest.mark.parametrize("answer", SHAPE_ANSWERS)
def test_json_is_gh_json_to_the_byte(witness, workdir, answer):
    witness.fake.script({key("api", "repos/o/r"): answer})
    seen = witness.compare(
        lambda: Before.gh_json("api", "repos/o/r"),
        lambda: GhTransport().json(["api", "repos/o/r"]),
    )
    assert seen["calls"] == ["api repos/o/r"]
    assert seen["invocations"][0]["cwd"] == str(workdir)


@pytest.mark.parametrize("answer", SHAPE_ANSWERS)
def test_probe_is_promotions_runner_to_the_byte(witness, workdir, tmp_path, answer):
    root = tmp_path / "root"
    root.mkdir()
    witness.fake.script({key("pr", "list", "--head", "develop"): answer})
    seen = witness.compare(
        lambda: Before.promote_gh(root, "pr", "list", "--head", "develop"),
        lambda: GhTransport().probe(["pr", "list", "--head", "develop"], cwd=root),
    )
    assert seen["invocations"][0]["cwd"] == str(root.resolve())


@pytest.mark.parametrize("answer", SHAPE_ANSWERS)
def test_merged_probe_is_the_merge_trains_runner_to_the_byte(witness, workdir, answer):
    witness.fake.script({key("pr", "edit", "7", "--add-label", "x"): answer})
    seen = witness.compare(
        lambda: Before.merge_train_gh("pr", "edit", "7", "--add-label", "x"),
        lambda: GhTransport().probe(
            ["pr", "edit", "7", "--add-label", "x"], strip=False, with_stderr=True
        ),
    )
    assert seen["invocations"][0]["cwd"] == str(workdir)


@pytest.mark.parametrize("answer", SHAPE_ANSWERS)
def test_survey_is_tidys_runner_to_the_byte(witness, workdir, tmp_path, answer):
    root = tmp_path / "root"
    root.mkdir()
    witness.fake.script({key("release", "list", "--json", "tagName"): answer})
    seen = witness.compare(
        lambda: Before.tidy_gh_json(root, "release", "list", "--json", "tagName"),
        lambda: GhTransport().survey(["release", "list", "--json", "tagName"], cwd=root),
    )
    assert seen["invocations"][0]["cwd"] == str(root.resolve())


def test_survey_is_tidys_runner_when_there_is_no_client_at_all(witness, tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    seen = witness.compare(
        lambda: Before.tidy_gh_json(tmp_path, "api", "x"),
        lambda: GhTransport().survey(["api", "x"], cwd=tmp_path),
    )
    assert seen["outcome"] == ("returned", ([], "the GitHub CLI (`gh`) is not installed"))
    assert seen["invocations"] == []


# ------------------------------------ before/after: github_state onto the transport


@pytest.mark.parametrize(
    ("args", "answer", "outcome"),
    [
        (
            ("pr", "view", "7", "--json", "number"),
            {"out": '{"number": 7}'},
            ("returned", {"number": 7}),
        ),
        (("pr", "list", "--json", "number"), {"out": ""}, ("returned", None)),
        (
            ("api", "graphql", "--raw-field", "query=q r", "--raw-field", "owner=o"),
            {"err": "HTTP 401: Bad credentials\n", "code": 1},
            (
                "raised",
                "RuntimeError",
                (
                    "gh api graphql --raw-field query=q r --raw-field owner=o: "
                    "HTTP 401: Bad credentials"
                ),
            ),
        ),
    ],
)
def test_gh_json_is_unchanged(witness, workdir, args, answer, outcome):
    witness.fake.script({key(*args): answer})
    seen = witness.compare(lambda: Before.gh_json(*args), lambda: github_state.gh_json(*args))
    assert seen["outcome"] == outcome
    assert seen["invocations"] == [{"argv": list(args), "cwd": str(workdir), "stdin": None}]


def test_repository_asks_gh_only_when_the_environment_does_not_say(witness, workdir, monkeypatch):
    monkeypatch.delenv("GH_REPO", raising=False)
    witness.fake.script(
        {key("repo", "view", "--json", "nameWithOwner"): {"out": '{"nameWithOwner": "o/r"}'}}
    )
    seen = witness.compare(Before.repository, github_state.repository)
    assert seen["outcome"] == ("returned", "o/r")
    assert seen["invocations"] == [
        {"argv": ["repo", "view", "--json", "nameWithOwner"], "cwd": str(workdir), "stdin": None}
    ]

    monkeypatch.setenv("GH_REPO", "explicit/repository")
    seen = witness.compare(Before.repository, github_state.repository)
    assert seen == {
        "outcome": ("returned", "explicit/repository"),
        "invocations": [],
        "calls": [],
    }


CREATE = ["pr", "comment", "7", "--repo", "o/r", "--body", BODY]
CREATE_ON_ISSUE = ["issue", "comment", "7", "--repo", "o/r", "--body", BODY]
REST_EDIT = [
    "api",
    "repos/o/r/issues/comments/9",
    "--method",
    "PATCH",
    "--field",
    f"body={BODY}",
]
GRAPHQL_EDIT = [
    "api",
    "graphql",
    "--field",
    f"query={MUTATION}",
    "--field",
    "id=IC_node",
    "--field",
    f"body={BODY}",
]
STATE = {"body": BODY}


@pytest.mark.parametrize(
    ("comments", "subject", "argv"),
    [
        ([], "pr", CREATE),
        ([{"body": "ordinary chatter", "databaseId": 3}], "pr", CREATE),
        ([], "issue", CREATE_ON_ISSUE),
        ([{**STATE, "databaseId": 9}], "pr", REST_EDIT),
        ([{**STATE, "databaseId": 1}, {**STATE, "databaseId": 9}], "pr", REST_EDIT),
        ([{**STATE, "databaseId": None, "id": "IC_node"}], "pr", GRAPHQL_EDIT),
    ],
)
def test_upsert_comment_builds_the_same_command(
    witness, workdir, monkeypatch, comments, subject, argv
):
    monkeypatch.setenv("GH_REPO", "o/r")
    witness.fake.script({key(*argv): {"out": "{}"}})
    seen = witness.compare(
        lambda: Before.upsert_comment(7, BODY, comments, PATTERN, subject=subject),
        lambda: github_state.upsert_comment(7, BODY, comments, PATTERN, subject=subject),
    )
    assert seen["outcome"] == ("returned", None)
    assert seen["invocations"] == [{"argv": argv, "cwd": str(workdir), "stdin": None}]


def test_upsert_comment_resolves_the_repository_through_the_same_call(
    witness, workdir, monkeypatch
):
    monkeypatch.delenv("GH_REPO", raising=False)
    view = ["repo", "view", "--json", "nameWithOwner"]
    witness.fake.script({key(*view): {"out": '{"nameWithOwner": "o/r"}'}, key(*CREATE): {}})
    seen = witness.compare(
        lambda: Before.upsert_comment(7, BODY, [], PATTERN),
        lambda: github_state.upsert_comment(7, BODY, [], PATTERN),
    )
    assert [call["argv"] for call in seen["invocations"]] == [view, CREATE]


def test_upsert_comment_fails_the_same_way(witness, workdir, monkeypatch):
    monkeypatch.setenv("GH_REPO", "o/r")
    witness.fake.script({key(*REST_EDIT): {"err": "HTTP 422\n", "code": 1}})
    comments = [{**STATE, "databaseId": 9}]
    seen = witness.compare(
        lambda: Before.upsert_comment(7, BODY, comments, PATTERN, error="could not save"),
        lambda: github_state.upsert_comment(7, BODY, comments, PATTERN, error="could not save"),
    )
    assert seen["outcome"] == ("raised", "RuntimeError", "could not save: HTTP 422")

    nameless = [STATE]
    seen = witness.compare(
        lambda: Before.upsert_comment(7, BODY, nameless, PATTERN),
        lambda: github_state.upsert_comment(7, BODY, nameless, PATTERN),
    )
    assert seen == {
        "outcome": (
            "raised",
            "RuntimeError",
            "could not persist automation state: comment has no ID",
        ),
        "invocations": [],
        "calls": [],
    }
