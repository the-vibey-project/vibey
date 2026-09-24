# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Storm work lives on durable storage, and a tool refuses to put it anywhere else (10.h).

On 2026-09-24 at about 09:09 EDT the operator's Mac rebooted mid-storm. macOS empties
/private/tmp at boot, and every storm worktree, the storm root (queue, run state, lanes,
evidence), the push lock, the benchmark evidence and the scratch probes lived under
/private/tmp/claude-501/storm/. Everything uncommitted went: about 1.5 hours of
concurrency-sweep measurements, a paper draft and three lanes of fixes. ADR-0057.

These hold `tools/storm_durability.py` to what the operator asked for:

1. one declared durable home for storm work (`VIBEY_STORM_HOME`, else `[paths] home` in
   storm.toml, else `~/git/vibey-storm`), from which the worktrees and the shared locks are
   derived;
2. a gate, not a judgement (12.d): a home, storm root or derived path that resolves under a
   volatile location -- through symlinks -- is refused with exit 78 and a message naming the
   key that moves it;
3. a throwaway storm (a test's) says so in its own storm.toml, with a reason, or it is
   refused like any other.

The volatile set is injected wherever a test needs a durable path, because a test's own
tmp_path is volatile by construction and the machine's $HOME may be too
(`HOME=$(mktemp -d) pytest` is a documented way to run this suite).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec and spec.loader, f"the storm tool is missing: {TOOLS / filename}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


storm_paths = _load("storm_paths", "storm_paths.py")
durability = _load("storm_durability", "storm_durability.py")

VolatileLocations = durability.VolatileLocations
StormHome = durability.StormHome
DurabilityGate = durability.DurabilityGate


def _locations(tmp_path: Path, environ: dict[str, str] | None = None) -> VolatileLocations:
    """A volatile set holding exactly one root, `tmp_path/volatile`, so the rest of tmp_path
    stands in for durable storage."""
    (tmp_path / "volatile").mkdir(exist_ok=True)
    return VolatileLocations(
        environ or {}, fixed=((str(tmp_path / "volatile"), "wiped in this test"),)
    )


# --- where the operating system discards files ------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/tmp/claude-501/storm/qwenstorm-3.0.0",
        "/private/tmp/claude-501/storm/.push-lock",
        "/var/tmp/bench",
        "/var/folders/xx/T/lane",
        "/dev/shm/storm",
        "/run/user/1000/storm",
    ],
)
def test_every_location_the_os_empties_is_volatile(path: str) -> None:
    found = VolatileLocations({}).containing(Path(path))
    assert found is not None, f"{path} was taken for durable storage"


def test_tmp_is_volatile_through_its_symlink() -> None:
    """On macOS /tmp is a symlink to /private/tmp. Resolved or not, it is the same place."""
    found = VolatileLocations({}).containing(Path("/tmp/x"))
    assert found is not None
    assert found[0] == Path("/tmp").resolve()


def test_the_temporary_directories_the_environment_names_are_volatile(tmp_path: Path) -> None:
    tmpdir, runtime = tmp_path / "t", tmp_path / "r"
    locations = VolatileLocations({"TMPDIR": str(tmpdir), "XDG_RUNTIME_DIR": str(runtime)})
    assert locations.containing(tmpdir / "lane") is not None
    assert locations.containing(runtime / "lock") is not None


def test_a_tmpdir_that_would_swallow_the_home_directory_is_ignored(tmp_path: Path) -> None:
    """TMPDIR=/ (or $HOME) would make every path volatile and so tell us nothing."""
    home = tmp_path / "home"
    for tmpdir in ("/", str(home), str(tmp_path)):
        locations = VolatileLocations({"TMPDIR": tmpdir, "HOME": str(home)}, fixed=())
        assert locations.containing(home / "git/vibey-storm") is None, tmpdir


def test_a_symlink_into_volatile_storage_is_volatile(tmp_path: Path) -> None:
    locations = _locations(tmp_path)
    (tmp_path / "durable").mkdir()
    (tmp_path / "durable/storm").symlink_to(tmp_path / "volatile")
    found = locations.containing(tmp_path / "durable/storm/lanes/x")
    assert found is not None
    assert found[0] == (tmp_path / "volatile").resolve()


def test_a_durable_path_is_not_volatile(tmp_path: Path) -> None:
    assert _locations(tmp_path).containing(tmp_path / "durable/git/vibey-storm") is None


def test_a_path_that_does_not_exist_yet_is_judged_by_where_it_would_be(tmp_path: Path) -> None:
    assert _locations(tmp_path).containing(tmp_path / "volatile/not/yet/made") is not None


# --- the one declared home --------------------------------------------------------------


def test_the_home_defaults_to_the_git_directory_already_in_use(tmp_path: Path) -> None:
    where, source = StormHome({"HOME": str(tmp_path)}).resolve()
    assert where == tmp_path / "git/vibey-storm"
    assert source == "default"


def test_the_environment_outranks_storm_toml(tmp_path: Path) -> None:
    root = tmp_path / "storm"
    root.mkdir()
    (root / "storm.toml").write_text('[paths]\nhome = "/srv/declared"\n', encoding="utf-8")
    assert StormHome({}, root).resolve() == (Path("/srv/declared"), f"[paths] home in {root}")
    env = {"VIBEY_STORM_HOME": "/srv/from-env"}
    assert StormHome(env, root).resolve() == (Path("/srv/from-env"), "VIBEY_STORM_HOME")


def test_a_relative_home_in_storm_toml_is_read_from_the_storm_root(tmp_path: Path) -> None:
    root = tmp_path / "storm"
    root.mkdir()
    (root / "storm.toml").write_text('[paths]\nhome = ".."\n', encoding="utf-8")
    assert StormHome({}, root).resolve()[0] == root / ".."


def test_a_relative_home_in_the_environment_is_refused() -> None:
    """Relative to what? The answer would change with the directory a tool was started in."""
    with pytest.raises(SystemExit) as refused:
        StormHome({"VIBEY_STORM_HOME": "vibey-storm"}).resolve()
    assert "VIBEY_STORM_HOME" in str(refused.value)


def test_worktrees_and_the_push_lock_are_derived_from_the_home(tmp_path: Path) -> None:
    home = StormHome({"VIBEY_STORM_HOME": str(tmp_path)})
    assert home.worktree("fix-durable-work-paths") == tmp_path / "fix-durable-work-paths"
    assert home.push_lock() == tmp_path / ".push-lock"
    for bad in ("", "..", "a/b", "../escape", ".hidden"):
        with pytest.raises(SystemExit):
            home.worktree(bad)


def test_the_push_gates_default_lock_is_the_homes(tmp_path: Path, monkeypatch) -> None:
    """The machine's shared lock follows the home, not wherever the tool happens to sit."""
    push_gate = _load("push_gate", "push_gate.py")
    root = tmp_path / "storm"
    root.mkdir()
    (root / "storm.toml").write_text('[paths]\nhome = "/srv/storm-home"\n', encoding="utf-8")
    monkeypatch.delenv("VIBEY_STORM_HOME", raising=False)
    cfg = push_gate.PushGateConfig.declared(root)
    assert cfg.lock == Path("/srv/storm-home/.push-lock")
    assert cfg.state_dir == Path("/srv/storm-home/.push-lock.gate")


# --- the gate -----------------------------------------------------------------------------


def test_the_gate_names_the_key_and_the_volatile_location(tmp_path: Path) -> None:
    gate = DurabilityGate(_locations(tmp_path))
    hits = gate.inspect({"storm home": tmp_path / "volatile/storm", "lanes": tmp_path / "x"})
    assert [hit.name for hit in hits] == ["storm home"]
    message = gate.refusal(hits, "VIBEY_STORM_HOME")
    assert "VIBEY_STORM_HOME" in message
    assert str((tmp_path / "volatile").resolve()) in message
    assert "wiped in this test" in message


def test_the_gate_refuses_with_exit_78(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    gate = DurabilityGate(_locations(tmp_path))
    with pytest.raises(SystemExit) as refused:
        gate.enforce({"storm root": tmp_path / "volatile/q"}, "VIBEY_STORM_HOME")
    assert refused.value.code == durability.VOLATILE_EXIT == 78
    assert "VIBEY_STORM_HOME" in capsys.readouterr().err


def test_the_gate_passes_durable_paths_silently(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    DurabilityGate(_locations(tmp_path)).enforce({"storm root": tmp_path / "d"}, "KEY")
    assert capsys.readouterr().err == ""


def test_a_throwaway_storm_passes_only_by_saying_so_with_a_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = tmp_path / "volatile/storm"
    root.mkdir(parents=True)
    gate = DurabilityGate(_locations(tmp_path), disposable_root=root)
    with pytest.raises(SystemExit):
        gate.enforce({"storm root": root}, "VIBEY_STORM_HOME")
    (root / "storm.toml").write_text('[durability]\ndisposable = ""\n', encoding="utf-8")
    with pytest.raises(SystemExit) as empty:
        DurabilityGate(_locations(tmp_path), disposable_root=root).enforce({"r": root}, "K")
    assert "disposable" in str(empty.value)
    (root / "storm.toml").write_text(
        '[durability]\ndisposable = "a test fixture"\n', encoding="utf-8"
    )
    DurabilityGate(_locations(tmp_path), disposable_root=root).enforce({"r": root}, "K")
    assert "a test fixture" in capsys.readouterr().err, "a disposable storm must say so"


# --- the command line ---------------------------------------------------------------------


def _cli(*argv: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / "storm_durability.py"), *argv],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def test_check_refuses_a_home_under_tmp(tmp_path: Path) -> None:
    env = {**os.environ, "VIBEY_STORM_HOME": "/tmp/claude-501/storm"}
    done = _cli("check", "--root", str(tmp_path), env=env)
    assert done.returncode == 78, done.stdout + done.stderr
    assert "VIBEY_STORM_HOME" in done.stderr
    assert "/tmp" in done.stderr


def test_check_refuses_an_extra_path_under_tmp(tmp_path: Path) -> None:
    root = tmp_path / "storm"
    root.mkdir()
    (root / "storm.toml").write_text('[durability]\ndisposable = "test"\n', encoding="utf-8")
    env = {**os.environ, "VIBEY_STORM_HOME": str(root)}
    done = _cli("check", "--root", str(root), "--path", "lane=/tmp/lane", env=env)
    assert done.returncode == 78, done.stdout + done.stderr
    assert "lane" in done.stderr


def test_status_reports_the_home_and_whether_it_is_durable(tmp_path: Path) -> None:
    env = {**os.environ, "VIBEY_STORM_HOME": "/tmp/claude-501/storm"}
    done = _cli("status", "--root", str(tmp_path), env=env)
    assert done.returncode == 78
    assert "VOLATILE" in done.stdout
    assert "VIBEY_STORM_HOME" in done.stdout


def test_worktree_prints_the_derived_path(tmp_path: Path) -> None:
    root = tmp_path / "storm"
    root.mkdir()
    (root / "storm.toml").write_text('[durability]\ndisposable = "test"\n', encoding="utf-8")
    env = {**os.environ, "VIBEY_STORM_HOME": str(root)}
    done = _cli("worktree", "fix-x", "--root", str(root), env=env)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str(root / "fix-x")


# --- the declared seam (ADR-0016) ---------------------------------------------------------


def test_every_class_honours_the_interface_declared_beside_it(tmp_path: Path) -> None:
    declared = _load("storm_durability_interface", "interfaces/storm_durability_interface.py")
    locations = _locations(tmp_path)
    pairs = [
        (locations, declared.VolatileLocationsInterface),
        (StormHome({}), declared.StormHomeInterface),
        (DurabilityGate(locations), declared.DurabilityGateInterface),
    ]
    for instance, interface in pairs:
        assert isinstance(instance, interface), interface.__name__


# --- the tools that place work are gated ----------------------------------------------------


@pytest.mark.parametrize(
    "tool", ["storm-queue.sh", "lane-setup.sh", "storm-cycle.py", "storm-watch.py"]
)
def test_the_tools_that_place_storm_work_consult_the_gate(tool: str) -> None:
    source = (TOOLS / tool).read_text(encoding="utf-8")
    assert "storm_durability" in source, f"{tool} places storm work without the durability gate"
