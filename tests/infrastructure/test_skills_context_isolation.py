# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The vibey-skills CLI is a child like any other: no worker environment, no planted code.

The compiler spawned `sys.executable -m vibey_skills.cli` with no `env=` and no `cwd`.
`-m` puts the current directory first on `sys.path`, so a `vibey_skills/` package
planted in the worker's working directory -- any process running as the worker's user
can write there -- ran in place of the real CLI, with every `VIBEY_*` variable the
worker held. Reproduced in review with a stand-in package that printed only variable
names; reproduced here the same way.
"""

import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from tests.application.fakes import make_job
from vibey.infrastructure.skills_context import VibeySkillsContextCompiler

_SECRETS = {
    "VIBEY_PG_URL": "postgresql://vibey:secret@db/vibey",
    "VIBEY_PG_MIGRATE_URL": "postgresql://owner:secret@db/vibey",
    "PGPASSWORD": "secret",
    "GH_TOKEN": "ghp_secret",
}


def _job():  # type: ignore[no-untyped-def]
    return replace(
        make_job(uuid4()),
        kind="build.implement",
        work_item_id="item-1",
        attempts=1,
        payload={"title": "t", "languages": ["python"]},
    )


def _recorder(log: Path) -> str:
    """Python that records the names of its environment and its working directory."""
    return (
        "import os, pathlib\n"
        f"log = pathlib.Path({str(log)!r})\n"
        "with log.open('a') as out:\n"
        "    out.write('cwd=' + os.getcwd() + '\\n')\n"
        "    out.write('\\n'.join(sorted(os.environ)) + '\\n')\n"
    )


@pytest.fixture
def worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The worker's own working directory, where a same-user process planted a package,
    and the worker's secrets in its environment."""
    cwd = tmp_path / "worker-cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    for name, value in _SECRETS.items():
        monkeypatch.setenv(name, value)
    return cwd


async def test_a_vibey_skills_package_planted_in_the_workers_cwd_does_not_run(
    worker: Path, tmp_path: Path
) -> None:
    marker = tmp_path / "planted-ran.log"
    planted = worker / "vibey_skills"
    planted.mkdir()
    (planted / "__init__.py").write_text(_recorder(marker))
    (planted / "cli.py").write_text(_recorder(marker))
    repo = tmp_path / "repo"
    repo.mkdir()
    compiler = VibeySkillsContextCompiler(mode="shadow", index_path=repo / "index")

    await compiler.compile(job=_job(), worktree_path=repo)

    assert not marker.exists(), marker.read_text()


async def test_the_skills_cli_starts_from_the_system_basics_in_a_directory_vibey_controls(
    worker: Path, tmp_path: Path
) -> None:
    log = tmp_path / "cli-env.log"
    script = tmp_path / "stand_in_cli.py"
    script.write_text(_recorder(log) + "raise SystemExit(1)\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    index = repo / ".vibey" / "skills-context" / "index"
    compiler = VibeySkillsContextCompiler(
        mode="shadow", index_path=index, command=(sys.executable, str(script))
    )

    await compiler.compile(job=_job(), worktree_path=repo)

    lines = log.read_text().splitlines()
    names = {line for line in lines if not line.startswith("cwd=")}
    assert "PATH" in names
    assert not {n for n in names if n.startswith(("VIBEY_", "PG"))}
    assert "GH_TOKEN" not in names
    # Not the worker's working directory: the index's own parent.
    assert f"cwd={index.parent.resolve()}" in {
        f"cwd={Path(line[4:]).resolve()}" for line in lines if line.startswith("cwd=")
    }


def test_the_default_command_runs_python_isolated() -> None:
    compiler = VibeySkillsContextCompiler(mode="shadow", index_path=Path("/tmp/index"))  # nosec B108

    assert compiler.command == (sys.executable, "-I", "-m", "vibey_skills.cli")
