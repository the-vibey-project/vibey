# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`GhStateRemote`: what it asks GitHub's git data API, what it sends, and what it reads back.

A fake `gh` answers each `gh api` call by method and path, and reads the JSON body from the
`--input` file while the call runs -- the file is gone afterwards -- so the bodies are pinned.
"""

import base64
import json
from pathlib import Path

import pytest

from vibey.application.interfaces.state_sync import StateRemote
from vibey.domain.errors import VibeyError
from vibey.domain.state_sync import RemoteHead, RemoteMoved
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.state.gh_state_remote import MESSAGE, GhStateError, GhStateRemote
from vibey.infrastructure.state.settings import StateSyncSettings
from vibey.infrastructure.workflows.gh_workflows import GhCliSubprocessExecutor

SETTINGS = StateSyncSettings(repository="o/r")
DATA = b"VBYSTAT1 sealed bytes \x00\xff"
PREFIX = "repos/o/r/"


def ok(document: object) -> CommandResult:
    return CommandResult(0, json.dumps(document), "")


def refused(code: int, *, on_stdout: bool = False) -> CommandResult:
    reason = f"gh: refused (HTTP {code})\n"
    return CommandResult(1, reason, "") if on_stdout else CommandResult(1, "", reason)


class FakeGh:
    """Answers `gh api -X METHOD repos/o/r/PATH [--input FILE]` by (METHOD, PATH)."""

    def __init__(
        self,
        answers: dict[tuple[str, str], CommandResult] | None = None,
        *,
        repo_view: CommandResult | None = None,
    ) -> None:
        self.answers = answers or {}
        self.repo_view = repo_view
        self.argv: list[tuple[str, ...]] = []
        self.calls: list[tuple[str, str, object]] = []
        self.inputs: list[Path] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.argv.append(argv)
        if argv[1:3] == ("repo", "view"):
            assert self.repo_view is not None
            return self.repo_view
        assert argv[1:3] == ("api", "-X")
        method, target = argv[3], argv[4]
        assert target.startswith(PREFIX)
        path = target.removeprefix(PREFIX)
        body: object = None
        if "--input" in argv:
            request = Path(argv[argv.index("--input") + 1])
            self.inputs.append(request)
            body = json.loads(request.read_text(encoding="utf-8"))
        self.calls.append((method, path, body))
        return self.answers[(method, path)]

    def body(self, method: str, path: str) -> object:
        return next(b for m, p, b in self.calls if (m, p) == (method, path))


def remote(fake: FakeGh, settings: StateSyncSettings = SETTINGS) -> GhStateRemote:
    return GhStateRemote(settings, "o/r", executor=fake)


def reads(
    commit: str = "c1", *, content: str | None = None
) -> dict[tuple[str, str], CommandResult]:
    """A commit whose tree holds the state file, and the blob it names."""
    encoded = base64.b64encode(DATA).decode()
    return {
        ("GET", f"git/commits/{commit}"): ok({"sha": commit, "tree": {"sha": "t1"}}),
        ("GET", "git/trees/t1"): ok(
            {
                "tree": [
                    "not an entry",
                    {"path": "README", "sha": "b0"},
                    {"path": "state.vibey", "sha": "b1"},
                ]
            }
        ),
        ("GET", "git/blobs/b1"): ok(
            {"content": content if content is not None else encoded[:8] + "\n" + encoded[8:]}
        ),
    }


def writes() -> dict[tuple[str, str], CommandResult]:
    return {
        ("POST", "git/blobs"): ok({"sha": "b9"}),
        ("POST", "git/trees"): ok({"sha": "t9"}),
        ("POST", "git/commits"): ok({"sha": "c9"}),
        ("POST", "git/refs"): ok({"ref": "refs/heads/vibey-state"}),
        ("PATCH", "git/refs/heads/vibey-state"): ok({"object": {"sha": "c9"}}),
    }


def test_the_remote_satisfies_its_interface() -> None:
    assert isinstance(remote(FakeGh()), StateRemote)
    assert issubclass(GhStateError, VibeyError)
    assert isinstance(GhStateRemote(SETTINGS, "o/r")._executor, GhCliSubprocessExecutor)


@pytest.mark.parametrize("repository", ["", "o", "o/r/x", "/o", "o/", "/"])
def test_a_repository_that_is_not_owner_name_is_refused(repository: str) -> None:
    with pytest.raises(ValueError, match="OWNER/NAME"):
        GhStateRemote(SETTINGS, repository, executor=FakeGh())


def test_the_name_is_the_repository_and_branch() -> None:
    settings = StateSyncSettings(branch="state/main")
    assert GhStateRemote(settings, "o/r", executor=FakeGh()).name == "o/r:state/main"


async def test_resolve_with_a_declared_repository_asks_gh_nothing() -> None:
    fake = FakeGh()
    resolved = await GhStateRemote.resolve(StateSyncSettings(repository="d/x"), executor=fake)
    assert resolved.name == "d/x:vibey-state"
    assert fake.argv == []
    assert resolved._executor is fake
    default = await GhStateRemote.resolve(StateSyncSettings(repository="d/x"))
    assert isinstance(default._executor, GhCliSubprocessExecutor)


async def test_resolve_without_a_repository_asks_gh_for_the_working_directorys() -> None:
    fake = FakeGh(repo_view=CommandResult(0, "w/d\n", ""))
    resolved = await GhStateRemote.resolve(StateSyncSettings(), executor=fake, gh="/bin/gh")
    assert resolved.name == "w/d:vibey-state"
    assert fake.argv == [
        ("/bin/gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    ]
    assert resolved._gh == "/bin/gh"


@pytest.mark.parametrize(
    "answer",
    [
        CommandResult(1, "", "no git remotes found\n"),
        CommandResult(1, "w/d\n", "partial\n"),
        CommandResult(0, "  \n", ""),
    ],
)
async def test_resolve_with_no_repository_anywhere_is_refused(answer: CommandResult) -> None:
    with pytest.raises(GhStateError, match="set VIBEY_STATE_REPOSITORY=OWNER/NAME"):
        await GhStateRemote.resolve(StateSyncSettings(), executor=FakeGh(repo_view=answer))


async def test_no_branch_is_no_head() -> None:
    fake = FakeGh({("GET", "git/ref/heads/vibey-state"): refused(404)})
    assert await remote(fake).head() is None
    assert fake.argv == [("gh", "api", "-X", "GET", "repos/o/r/git/ref/heads/vibey-state")]


async def test_a_ref_without_a_commit_is_no_head() -> None:
    fake = FakeGh({("GET", "git/ref/heads/vibey-state"): ok({"object": "not an object"})})
    assert await remote(fake).head() is None


async def test_the_head_is_read_through_commit_tree_and_blob() -> None:
    fake = FakeGh(
        {("GET", "git/ref/heads/vibey-state"): ok({"object": {"sha": "c1"}}), **reads("c1")}
    )
    assert await remote(fake).head() == RemoteHead("c1", DATA)
    assert [(m, p) for m, p, _ in fake.calls] == [
        ("GET", "git/ref/heads/vibey-state"),
        ("GET", "git/commits/c1"),
        ("GET", "git/trees/t1"),
        ("GET", "git/blobs/b1"),
    ]
    assert all(body is None for _, _, body in fake.calls)
    assert all("--input" not in argv for argv in fake.argv)


async def test_a_head_whose_commit_cannot_be_read_is_an_error() -> None:
    fake = FakeGh(
        {
            ("GET", "git/ref/heads/vibey-state"): ok({"object": {"sha": "c1"}}),
            ("GET", "git/commits/c1"): refused(404),
        }
    )
    with pytest.raises(GhStateError, match="head c1 cannot be read"):
        await remote(fake).head()


async def test_a_commit_that_is_not_there_reads_as_nothing() -> None:
    fake = FakeGh({("GET", "git/commits/gone"): refused(404)})
    assert await remote(fake).at("gone") is None


async def test_a_commit_reads_back_its_state() -> None:
    assert await remote(FakeGh(reads("c2"))).at("c2") == DATA


@pytest.mark.parametrize(
    "tree",
    [
        ok({"tree": [{"path": "README", "sha": "b0"}]}),
        ok({"tree": [{"path": "state.vibey", "sha": 7}]}),
        ok({"tree": "not a list"}),
        ok({}),
        refused(404),
    ],
)
async def test_a_tree_without_the_state_file_is_an_error(tree: CommandResult) -> None:
    fake = FakeGh(
        {("GET", "git/commits/c1"): ok({"tree": {"sha": "t1"}}), ("GET", "git/trees/t1"): tree}
    )
    with pytest.raises(GhStateError, match="o/r:vibey-state at c1 holds no state.vibey"):
        await remote(fake).at("c1")


@pytest.mark.parametrize("blob", [ok({"sha": "b1"}), ok({"content": None}), refused(404)])
async def test_a_blob_without_content_is_an_error(blob: CommandResult) -> None:
    answers = reads("c1")
    answers[("GET", "git/blobs/b1")] = blob
    with pytest.raises(GhStateError, match="the blob b1 has no content"):
        await remote(FakeGh(answers)).at("c1")


@pytest.mark.parametrize("on_stdout", [False, True])
async def test_a_refused_read_is_an_error_not_an_absence(on_stdout: bool) -> None:
    fake = FakeGh({("GET", "git/ref/heads/vibey-state"): refused(500, on_stdout=on_stdout)})
    with pytest.raises(GhStateError, match=r"GitHub refused GET git/ref/heads/vibey-state: .*500"):
        await remote(fake).head()


async def test_a_read_refused_with_no_reason_is_still_an_error() -> None:
    fake = FakeGh({("GET", "git/ref/heads/vibey-state"): CommandResult(1, "", "")})
    with pytest.raises(GhStateError, match="GitHub refused GET"):
        await remote(fake).head()


@pytest.mark.parametrize("stdout", ["[]", '"text"', "3", "null"])
async def test_an_answer_that_is_not_an_object_is_an_error(stdout: str) -> None:
    fake = FakeGh({("GET", "git/ref/heads/vibey-state"): CommandResult(0, stdout, "")})
    with pytest.raises(GhStateError, match="with something not an object"):
        await remote(fake).head()


async def test_the_first_push_makes_blob_tree_commit_and_branch() -> None:
    fake = FakeGh(writes())
    assert await remote(fake).push(DATA, None) == "c9"
    assert [(m, p) for m, p, _ in fake.calls] == [
        ("POST", "git/blobs"),
        ("POST", "git/trees"),
        ("POST", "git/commits"),
        ("POST", "git/refs"),
    ]
    assert fake.body("POST", "git/blobs") == {
        "content": base64.b64encode(DATA).decode(),
        "encoding": "base64",
    }
    blob = fake.body("POST", "git/blobs")
    assert isinstance(blob, dict) and base64.b64decode(blob["content"]) == DATA
    assert fake.body("POST", "git/trees") == {
        "tree": [{"path": "state.vibey", "mode": "100644", "type": "blob", "sha": "b9"}]
    }
    assert fake.body("POST", "git/commits") == {"message": MESSAGE, "tree": "t9", "parents": []}
    assert fake.body("POST", "git/refs") == {"ref": "refs/heads/vibey-state", "sha": "c9"}
    # Every body went through a file that no longer exists.
    assert len(fake.inputs) == 4
    assert not any(path.exists() for path in fake.inputs)
    assert all(argv[-2] == "--input" for argv in fake.argv)


async def test_a_push_onto_a_parent_moves_the_branch_without_force() -> None:
    settings = StateSyncSettings(repository="o/r", branch="state", path="db.sealed")
    answers = writes()
    answers[("PATCH", "git/refs/heads/state")] = CommandResult(0, "", "")
    fake = FakeGh(answers)
    assert await remote(fake, settings).push(DATA, "c1") == "c9"
    assert [(m, p) for m, p, _ in fake.calls][-1] == ("PATCH", "git/refs/heads/state")
    assert fake.body("POST", "git/commits") == {"message": MESSAGE, "tree": "t9", "parents": ["c1"]}
    assert fake.body("POST", "git/trees") == {
        "tree": [{"path": "db.sealed", "mode": "100644", "type": "blob", "sha": "b9"}]
    }
    assert fake.body("PATCH", "git/refs/heads/state") == {"sha": "c9", "force": False}
    assert ("POST", "git/refs") not in [(m, p) for m, p, _ in fake.calls]


@pytest.mark.parametrize("code", [409, 422])
async def test_a_ref_update_github_refuses_as_moved_is_remote_moved(code: int) -> None:
    answers = writes()
    answers[("PATCH", "git/refs/heads/vibey-state")] = refused(code)
    with pytest.raises(RemoteMoved, match=f"o/r:vibey-state moved: .*HTTP {code}"):
        await remote(FakeGh(answers)).push(DATA, "c1")


async def test_a_branch_someone_else_started_first_is_remote_moved() -> None:
    answers = writes()
    answers[("POST", "git/refs")] = refused(422)
    with pytest.raises(RemoteMoved, match="moved"):
        await remote(FakeGh(answers)).push(DATA, None)


async def test_a_branch_gone_under_the_push_is_remote_moved() -> None:
    answers = writes()
    answers[("PATCH", "git/refs/heads/vibey-state")] = refused(404)
    with pytest.raises(RemoteMoved, match="o/r:vibey-state is gone"):
        await remote(FakeGh(answers)).push(DATA, "c1")


async def test_a_branch_github_cannot_start_is_an_error() -> None:
    answers = writes()
    answers[("POST", "git/refs")] = refused(404)
    with pytest.raises(GhStateError, match="could not start o/r:vibey-state"):
        await remote(FakeGh(answers)).push(DATA, None)


@pytest.mark.parametrize("step", ["git/blobs", "git/trees", "git/commits"])
@pytest.mark.parametrize("code", [409, 422, 403])
async def test_a_refused_object_is_a_refusal_not_a_race(step: str, code: int) -> None:
    answers = writes()
    answers[("POST", step)] = refused(code)
    with pytest.raises(GhStateError, match=f"GitHub refused POST {step}: .*HTTP {code}") as raised:
        await remote(FakeGh(answers)).push(DATA, "c1")
    assert not isinstance(raised.value, RemoteMoved)


@pytest.mark.parametrize("step", ["git/blobs", "git/trees", "git/commits"])
@pytest.mark.parametrize("answer", [ok({}), ok({"sha": 9}), refused(404)])
async def test_an_object_github_did_not_make_is_an_error(step: str, answer: CommandResult) -> None:
    answers = writes()
    answers[("POST", step)] = answer
    fake = FakeGh(answers)
    with pytest.raises(GhStateError, match="did not make the commit for o/r:vibey-state"):
        await remote(fake).push(DATA, "c1")
    assert not any(p.startswith("git/refs") for _, p, _ in fake.calls)
