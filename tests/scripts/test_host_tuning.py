# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/host_tuning.py` and the host-health pieces that measure its effect: every item's
gate, each backend's observe/apply/undo on macOS and Linux fixture output, the append-only
journal, and the weekly probes (model loads, the memory and write budget, tuning state).

Everything that could reach the host is a fake: the command runner answers by argv prefix,
the file tree is a tmp directory, the platform and the clock are fixed. A fixture makes any
real subprocess fail loudly, so a test can never pass or fail with the machine it runs on.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import gzip
import json
import plistlib
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from scripts import host_health as hh
from scripts import host_tuning as ht
from scripts import minimum_specs as ms

REPO = Path(__file__).resolve().parents[2]
SETTINGS = ht.TuningSettings.load(REPO / "scripts/host_tuning.toml")
HEALTH = hh.HealthSettings.load(REPO / hh.DEFAULT_CONFIG)
NOW = "2026-10-05T06:41:00.000Z"
NOW_EPOCH = 1_791_182_460.0  # 2026-10-05T06:41:00Z


class FakeRunner:
    """Answers commands by their first matching prefix; records every call."""

    def __init__(self, answers: Mapping[tuple[str, ...], Any] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[list[str]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> ms.CommandResult:
        self.calls.append(list(argv))
        for prefix, answer in self.answers.items():
            if tuple(argv[: len(prefix)]) == prefix:
                return answer(list(argv)) if callable(answer) else answer
        return ms.CommandResult(127, "", f"no answer for {argv[:3]}", 0.0)


def ok(stdout: str = "", code: int = 0) -> ms.CommandResult:
    return ms.CommandResult(code, stdout, "", 0.0)


def ps_line(epoch: float, command: str) -> str:
    return time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(epoch)) + " " + command


def ctx(
    tmp_path: Path,
    answers: Mapping[tuple[str, ...], Any] | None = None,
    system: str = "Darwin",
    now: str = NOW,
) -> ht.TuningContext:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    return ht.TuningContext(FakeRunner(answers), system, lambda: now, 5.0, home, root)


def settings_with(**items: Mapping[str, Any]) -> ht.TuningSettings:
    """The declared settings with some items' keys overridden (an adopted B item, say)."""
    table = json.loads(json.dumps(SETTINGS.table))
    for key, overrides in items.items():
        table["items"][key].update(overrides)
    return ht.TuningSettings(table)


def item(key: str, settings: ht.TuningSettings = SETTINGS) -> ht.TuningItem:
    return next(i for i in settings.items() if i.key == key)


@pytest.fixture(autouse=True)
def _the_host_is_out_of_reach(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a test reached the real host: a subprocess")

    monkeypatch.setattr(ms.SubprocessRunner, "run", refuse)


# ------------------------------------------------------------------------ the declaration


def test_every_declared_item_has_what_its_kind_and_class_need() -> None:
    needs = {
        "env": ("service", "name", "value"),
        "docker_desktop": ("key", "value", "where"),
        "postgres": ("name", "value"),
        "reclaim": ("path", "measure", "command", "timeout_s", "why_regenerable"),
        "log": ("path", "max_mib", "keep"),
        "ollama_loads": ("service", "window_hours", "max_distinct_num_ctx", "max_loads_per_day"),
        "models": ("service", "stale_after_days"),
    }
    for i in SETTINGS.items():
        for key in ("label", "class", "kind", "expected", "risk", "evidence", "judged_by"):
            assert i.spec[key], (i.key, key)
        for key in needs[i.kind]:
            assert key in i.spec, (i.key, key)
        assert i.klass in SETTINGS["gates"], i.key
        if i.klass == "B":
            assert i.spec["adopted"] is False, f"{i.key}: adopted before its canary ran"
        if i.klass == "C":
            assert i.spec["operator_approved"] == "", f"{i.key}: approved without the operator"


def test_nothing_that_can_touch_the_model_is_class_a() -> None:
    for i in SETTINGS.items():
        if i.kind in ("env", "ollama_loads"):
            assert i.klass == "B", i.key


def test_the_gates() -> None:
    gates = SETTINGS["gates"]
    assert item("uv_cache").gate(gates) == (True, "class A: safe now")
    assert item("ollama_kv_cache_type").gate(gates)[0] is False
    adopted = settings_with(ollama_kv_cache_type={"adopted": True})
    assert item("ollama_kv_cache_type", adopted).gate(gates) == (True, "class B: adopted")
    assert item("docker_kubernetes").gate(gates)[0] is False
    approved = settings_with(docker_kubernetes={"operator_approved": "PR #9999"})
    assert "PR #9999" in item("docker_kubernetes", approved).gate(gates)[1]
    broken = ht.TuningItem("x", {"class": "Z"})
    with pytest.raises(KeyError):
        broken.gate({"Z": "whenever"})


def test_an_observation_refuses_an_unknown_state() -> None:
    with pytest.raises(ValueError, match="unknown state"):
        ht.Observation("k", "A", "log", "l", None, None, "fine", "", True)


# ------------------------------------------------------------------------ the environment


def test_an_unset_class_b_variable_is_proposed_not_drift(tmp_path: Path) -> None:
    c = ctx(tmp_path, {("launchctl", "getenv"): ok("", 1)})
    tuner = ht.HostTuner(SETTINGS, c)
    seen = tuner.observe(item("ollama_max_loaded_models"))
    assert seen.state == "proposed" and not seen.wants_attention
    assert "unset" in seen.detail


def test_an_adopted_variable_is_applied_journalled_and_reasserted_at_login(tmp_path: Path) -> None:
    adopted = settings_with(ollama_kv_cache_type={"adopted": True})
    runner_calls: list[list[str]] = []

    def setenv(argv: list[str]) -> ms.CommandResult:
        runner_calls.append(argv)
        return ok()

    c = ctx(tmp_path, {("launchctl", "getenv"): ok("f16\n"), ("launchctl", "setenv"): setenv})
    tuner = ht.HostTuner(adopted, c)
    assert tuner.observe(item("ollama_kv_cache_type", adopted)).state == "drift"
    lines = tuner.apply(["ollama_kv_cache_type"])
    assert runner_calls == [["launchctl", "setenv", "OLLAMA_KV_CACHE_TYPE", "q8_0"]]
    assert any("was f16" in line for line in lines)
    assert any("never does" in line for line in lines), "a restart is said, not done"
    entry = tuner.journal.last("ollama_kv_cache_type", ("apply",))
    assert entry is not None and entry["prior"] == "f16" and entry["value"] == "q8_0"
    agent = c.home / "Library/LaunchAgents/dev.vibey.host-tuning.ollama-env.plist"
    body = plistlib.loads(agent.read_bytes())
    assert body["RunAtLoad"] is True
    assert "/bin/launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0" in body["ProgramArguments"][2]
    assert not any(call[:1] in (["osascript"], ["open"]) for call in c.runner.calls)


def test_a_change_the_running_server_predates_is_pending_restart(tmp_path: Path) -> None:
    adopted = settings_with(ollama_num_parallel={"adopted": True})
    applied = NOW_EPOCH - 3600
    ps = "\n".join(
        [
            ps_line(applied - 86400, "/Applications/Ollama.app/Contents/Resources/ollama serve"),
            ps_line(applied - 60, "/x/llama-server --model m -c 65536 -np 1 --flash-attn auto"),
        ]
    )
    c = ctx(tmp_path, {("launchctl", "getenv"): ok("1\n"), ("ps",): ok(ps)})
    tuner = ht.HostTuner(adopted, c)
    tuner.journal.append(
        {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(applied)),
            "key": "ollama_num_parallel",
            "kind": "env",
            "action": "apply",
            "service": "ollama",
            "name": "OLLAMA_NUM_PARALLEL",
            "value": "1",
            "prior": None,
        }
    )
    seen = tuner.observe(item("ollama_num_parallel", adopted))
    assert seen.state == "pending-restart" and seen.wants_attention
    assert "-np 1" in seen.detail and "Ollama app" in seen.detail


def test_a_restarted_server_has_it_in_force_and_shows_what_the_runner_got(tmp_path: Path) -> None:
    ps = "\n".join(
        [
            ps_line(NOW_EPOCH - 600, "/Applications/Ollama.app/Contents/Resources/ollama serve"),
            ps_line(NOW_EPOCH - 60, "/x/llama-server -c 65536 -np 1 --flash-attn auto"),
        ]
    )
    c = ctx(tmp_path, {("launchctl", "getenv"): ok("1\n"), ("ps",): ok(ps)})
    seen = ht.HostTuner(SETTINGS, c).observe(item("ollama_flash_attention"))
    assert seen.state == "in-force"
    assert "--flash-attn auto" in seen.detail


def test_a_kv_cache_type_the_server_never_passed_on_is_not_received(tmp_path: Path) -> None:
    """ADR-0045: Ollama 0.34.2 accepted OLLAMA_KV_CACHE_TYPE and never handed it to
    llama-server. The runner's argv is the proof, not the environment."""
    adopted = settings_with(ollama_kv_cache_type={"adopted": True})
    ps = ps_line(NOW_EPOCH - 60, "/x/llama-server -c 65536 -np 1 --flash-attn auto")
    c = ctx(tmp_path, {("launchctl", "getenv"): ok("q8_0\n"), ("ps",): ok(ps)})
    seen = ht.HostTuner(adopted, c).observe(item("ollama_kv_cache_type", adopted))
    assert seen.state == "not-received" and seen.wants_attention
    assert "no --cache-type-k" in seen.detail


def test_undo_restores_the_prior_value_and_drops_it_from_the_login_agent(tmp_path: Path) -> None:
    adopted = settings_with(
        ollama_keep_alive={"adopted": True}, ollama_max_loaded_models={"adopted": True}
    )
    values: dict[str, str] = {"OLLAMA_KEEP_ALIVE": "5m"}

    def launchctl(argv: list[str]) -> ms.CommandResult:
        if argv[1] == "getenv":
            return ok(values.get(argv[2], ""), 0 if argv[2] in values else 1)
        if argv[1] == "setenv":
            values[argv[2]] = argv[3]
        else:
            values.pop(argv[2], None)
        return ok()

    c = ctx(tmp_path, {("launchctl",): launchctl})
    tuner = ht.HostTuner(adopted, c)
    tuner.apply(["ollama_keep_alive", "ollama_max_loaded_models"])
    assert values == {"OLLAMA_KEEP_ALIVE": "15m", "OLLAMA_MAX_LOADED_MODELS": "1"}
    assert any("restored to 5m" in line for line in tuner.undo("ollama_keep_alive"))
    assert any("restored to unset" in line for line in tuner.undo("ollama_max_loaded_models"))
    assert values == {"OLLAMA_KEEP_ALIVE": "5m"}
    agent = c.home / "Library/LaunchAgents/dev.vibey.host-tuning.ollama-env.plist"
    assert not agent.exists(), "nothing applied remains, so no agent re-asserts anything"
    assert tuner.undo("ollama_keep_alive")[0].endswith("no standing change by this tool")
    assert tuner.journal.applied_env("ollama") == {}


def test_a_failed_undo_is_reported_and_a_kind_that_changed_nothing_has_nothing_to_undo(
    tmp_path: Path,
) -> None:
    c = ctx(tmp_path, {("launchctl",): ok("", 3)})
    tuner = ht.HostTuner(SETTINGS, c)
    for key, kind in (("ollama_keep_alive", "env"), ("docker_kubernetes", "docker_desktop")):
        tuner.journal.append(
            {
                "at": NOW,
                "key": key,
                "kind": kind,
                "action": "apply",
                "service": "ollama",
                "name": "OLLAMA_KEEP_ALIVE",
                "value": "15m",
                "prior": None,
            }
        )
    tuner.journal.append(
        {"at": NOW, "key": "x", "kind": "env", "service": "ollama", "action": "rotate"}
    )
    assert "launchctl unsetenv OLLAMA_KEEP_ALIVE failed" in tuner.undo("ollama_keep_alive")[0]
    assert tuner.undo("docker_kubernetes")[0].endswith("this tool changed nothing for it")


def test_a_failed_launchctl_is_reported_and_not_journalled(tmp_path: Path) -> None:
    adopted = settings_with(ollama_keep_alive={"adopted": True})
    c = ctx(tmp_path, {("launchctl", "getenv"): ok("", 1), ("launchctl", "setenv"): ok("", 5)})
    tuner = ht.HostTuner(adopted, c)
    assert "failed" in tuner.apply(["ollama_keep_alive"])[0]
    assert tuner.journal.entries() == []


def test_linux_stages_a_drop_in_and_never_runs_sudo(tmp_path: Path) -> None:
    adopted = settings_with(ollama_max_loaded_models={"adopted": True})
    show = ok('OLLAMA_HOST=127.0.0.1:11434 "OLLAMA_MODELS=/srv/my models"\n')
    c = ctx(tmp_path, {("systemctl", "show"): show}, system="Linux")
    tuner = ht.HostTuner(adopted, c)
    assert tuner.observe(item("ollama_max_loaded_models", adopted)).state == "drift"
    lines = tuner.apply(["ollama_max_loaded_models"])
    staged = c.home / ".local/state/vibey/host-tuning/staged/vibey-host-tuning.conf"
    assert staged.read_text() == '[Service]\nEnvironment="OLLAMA_MAX_LOADED_MODELS=1"\n'
    assert any("sudo install -D -m 0644" in line for line in lines)
    assert not any("sudo" in call for call in c.runner.calls)
    tuner.undo("ollama_max_loaded_models")
    assert staged.read_text() == "[Service]\n"


def test_linux_reads_the_units_environment(tmp_path: Path) -> None:
    show = ok("OLLAMA_NUM_PARALLEL=1 OLLAMA_HOST=0.0.0.0\n")
    ps = ps_line(NOW_EPOCH - 60, "/usr/local/bin/ollama serve")
    c = ctx(tmp_path, {("systemctl", "show"): show, ("ps",): ok(ps)}, system="Linux")
    seen = ht.HostTuner(SETTINGS, c).observe(item("ollama_num_parallel"))
    assert seen.state == "in-force"
    unreadable = ctx(tmp_path, {("systemctl", "show"): ok("", 1)}, system="Linux")
    assert ht.HostTuner(SETTINGS, unreadable).observe(item("ollama_num_parallel")).actual is None


# ------------------------------------------------------------------------ desktop, database


def write_docker(c: ht.TuningContext, data: Mapping[str, Any]) -> Path:
    path = c.home / "Library/Group Containers/group.com.docker/settings-store.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


def test_docker_desktop_settings_are_observed_and_never_written(tmp_path: Path) -> None:
    c = ctx(tmp_path)
    path = write_docker(c, {"KubernetesEnabled": True, "MemoryMiB": 8192})
    tuner = ht.HostTuner(SETTINGS, c)
    assert tuner.observe(item("docker_kubernetes")).state == "proposed"
    assert tuner.observe(item("docker_memory_cap")).state == "in-force"
    approved = settings_with(docker_kubernetes={"operator_approved": "2026-10-02"})
    before = path.read_text()
    lines = ht.HostTuner(approved, c).apply(["docker_kubernetes"])
    assert "Enable Kubernetes" in lines[0] and "for the operator" in lines[0]
    assert path.read_text() == before
    assert (
        ht.HostTuner(approved, c)
        .undo("docker_kubernetes")[0]
        .endswith("no standing change by this tool")
    )


def test_docker_desktop_is_absent_unreadable_or_not_applicable(tmp_path: Path) -> None:
    c = ctx(tmp_path)
    assert ht.HostTuner(SETTINGS, c).observe(item("docker_kubernetes")).state == "absent"
    write_docker(c, {}).write_text("{not json")
    assert ht.HostTuner(SETTINGS, c).observe(item("docker_kubernetes")).state == "unknown"
    linux = ctx(tmp_path, system="Linux")
    assert (
        ht.HostTuner(SETTINGS, linux).observe(item("docker_memory_cap")).state == "not-applicable"
    )


def psql(answers: dict[str, str], calls: list[str], fail: str = "") -> Any:
    def run(argv: list[str]) -> ms.CommandResult:
        sql = argv[-1]
        calls.append(sql)
        if fail and sql.startswith(fail):
            return ms.CommandResult(1, "", "ERROR: permission denied", 0.0)
        for start, out in answers.items():
            if sql.startswith(start):
                return ok(out + "\n")
        return ok("")

    return run


def test_postgres_is_observed_set_with_its_prior_and_reset_on_undo(tmp_path: Path) -> None:
    approved = settings_with(
        postgres_shared_buffers={"operator_approved": "PR #1", "value": "256MB"}
    )
    calls: list[str] = []
    answers = {
        "SHOW shared_buffers": "128MB",
        "SELECT source": "default",
        "SELECT context": "postmaster",
    }
    c = ctx(tmp_path, {("psql",): psql(answers, calls)})
    tuner = ht.HostTuner(approved, c)
    assert tuner.observe(item("postgres_shared_buffers", approved)).state == "drift"
    lines = tuner.apply(["postgres_shared_buffers"])
    assert "ALTER SYSTEM SET shared_buffers = '256MB'" in calls
    assert "SELECT pg_reload_conf()" in calls
    assert "next restart" in lines[0] and "was 128MB, from default" in lines[0]
    lines = tuner.undo("postgres_shared_buffers")
    assert "ALTER SYSTEM RESET shared_buffers" in calls
    assert "restored to 128MB" in lines[0]


def test_postgres_undo_pins_a_prior_that_was_not_the_default(tmp_path: Path) -> None:
    approved = settings_with(postgres_shared_buffers={"operator_approved": "x", "value": "256MB"})
    calls: list[str] = []
    answers = {"SHOW": "64MB", "SELECT source": "configuration file", "SELECT context": "sighup"}
    tuner = ht.HostTuner(approved, ctx(tmp_path, {("psql",): psql(answers, calls)}))
    assert tuner.apply(["postgres_shared_buffers"])[0].endswith("reloaded")
    tuner.undo("postgres_shared_buffers")
    assert "ALTER SYSTEM SET shared_buffers = '64MB'" in calls


def test_postgres_failures_are_reported(tmp_path: Path) -> None:
    approved = settings_with(postgres_shared_buffers={"operator_approved": "x", "value": "1GB"})
    calls: list[str] = []
    c = ctx(tmp_path, {("psql",): psql({"SHOW": "128MB"}, calls, fail="ALTER")})
    tuner = ht.HostTuner(approved, c)
    assert "failed" in tuner.apply(["postgres_shared_buffers"])[0]
    assert tuner.journal.entries() == []
    tuner.journal.append(
        {
            "at": NOW,
            "key": "postgres_shared_buffers",
            "kind": "postgres",
            "action": "apply",
            "prior": "128MB",
            "prior_source": "default",
        }
    )
    assert "failed" in tuner.undo("postgres_shared_buffers")[0]
    down = ctx(tmp_path, {("psql",): ok("", 2)})
    assert ht.HostTuner(SETTINGS, down).observe(item("postgres_shared_buffers")).state == "unknown"


def test_a_postgres_name_that_is_not_a_name_is_refused(tmp_path: Path) -> None:
    hostile = settings_with(postgres_shared_buffers={"name": "x; DROP TABLE jobs"})
    seen = ht.HostTuner(hostile, ctx(tmp_path)).observe(item("postgres_shared_buffers", hostile))
    assert seen.state == "unknown" and "not a Postgres setting name" in seen.detail


# ------------------------------------------------------------------------ reclaim and logs


def test_reclaim_sizes_parse() -> None:
    assert ht.ReclaimBackend.parse(["du", "-sk", "x"], "79691776\t/x\n") == 79_691_776 * 1024
    assert ht.ReclaimBackend.parse(["du"], "du: cannot read\n") is None
    du = "Reclaimable:\t6.814GB\nTotal:\t\t6.814GB\n"
    assert ht.ReclaimBackend.parse(["docker", "builder", "du"], du) == 6_814_000_000
    assert ht.ReclaimBackend.parse(["docker"], "nothing") is None


def test_reclaim_lists_target_size_and_why_then_journals_before_and_after(tmp_path: Path) -> None:
    sizes = iter(["80000000\t/c\n", "80000000\t/c\n", "30000000\t/c\n"])
    c = ctx(tmp_path, {("du",): lambda argv: ok(next(sizes)), ("uv", "cache", "prune"): ok()})
    (c.home / ".cache/uv").mkdir(parents=True)
    lines = ht.HostTuner(SETTINGS, c).apply(["uv_cache"], dry_run=False)
    assert "target ~/.cache/uv, 81.92 GB; regenerable:" in lines[0]
    assert lines[1].endswith("(freed 51.20 GB)")
    entry = ht.TuningJournal(c.path("~/.local/state/vibey/host-tuning/journal.jsonl")).last(
        "uv_cache", ("reclaim",)
    )
    assert entry is not None and entry["before"] - entry["after"] == 51_200_000_000
    assert "not reversible, by design" in ht.HostTuner(SETTINGS, c).undo("uv_cache")[0]


def test_a_uv_prune_is_refused_under_uv_run_which_would_make_it_wait_on_itself(
    tmp_path: Path,
) -> None:
    c = ctx(tmp_path, {("du",): ok("100\t/c\n")})
    c = ht.TuningContext(
        c.runner, "Darwin", c.now, 5.0, c.home, c.root, {"UV_RUN_RECURSION_DEPTH": "1"}
    )
    (c.home / ".cache/uv").mkdir(parents=True)
    lines = ht.HostTuner(SETTINGS, c).apply(["uv_cache"])
    assert "UV_RUN_RECURSION_DEPTH is set" in lines[0]
    assert ["uv", "cache", "prune"] not in c.runner.calls


def test_reclaim_that_times_out_or_fails_says_so(tmp_path: Path) -> None:
    c = ctx(
        tmp_path,
        {
            ("du",): ok("100\t/c\n"),
            ("uv",): ok("", 124),
            ("npm",): ms.CommandResult(1, "", "EACCES", 0.0),
        },
    )
    (c.home / ".cache/uv").mkdir(parents=True)
    (c.home / ".npm/_cacache").mkdir(parents=True)
    tuner = ht.HostTuner(SETTINGS, c)
    assert "timed out" in tuner.apply(["uv_cache"])[1]
    assert "exited 1: EACCES" in tuner.apply(["npm_cache"])[1]


def test_reclaim_observation(tmp_path: Path) -> None:
    c = ctx(
        tmp_path, {("docker", "builder", "du"): ok("Reclaimable:\t1.5GB\n"), ("du",): ok("", 124)}
    )
    tuner = ht.HostTuner(SETTINGS, c)
    assert tuner.observe(item("uv_cache")).state == "absent"
    (c.home / ".cache/uv").mkdir(parents=True)
    assert tuner.observe(item("uv_cache")).state == "unknown"
    seen = tuner.observe(item("docker_build_cache"))
    assert seen.state == "reclaimable" and seen.actual == 1_500_000_000
    assert not seen.wants_attention, "a cache is never drift"
    plan = tuner.apply(["docker_build_cache"], dry_run=True)
    assert plan[0].startswith("docker_build_cache: would apply")
    assert ["docker", "builder", "prune"] not in [call[:3] for call in c.runner.calls]


def test_a_log_over_its_limit_is_rotated_keeping_the_declared_number(tmp_path: Path) -> None:
    small = settings_with(postgres_log={"max_mib": 1, "keep": 2})
    c = ctx(tmp_path)
    log = c.path("/opt/homebrew/var/log/postgresql@18.log")
    log.parent.mkdir(parents=True)
    tuner = ht.HostTuner(small, c)
    assert tuner.observe(item("postgres_log", small)).state == "absent"
    for round_ in range(3):
        log.write_bytes(bytes([65 + round_]) * (2 * ht.MIB))
        seen = tuner.observe(item("postgres_log", small))
        assert seen.state == "over-limit" and seen.wants_attention
        assert "rotated" in tuner.apply(["postgres_log"])[0]
        assert log.stat().st_size == 0
    assert gzip.decompress(log.with_name(log.name + ".1.gz").read_bytes())[:1] == b"C"
    assert gzip.decompress(log.with_name(log.name + ".2.gz").read_bytes())[:1] == b"B"
    assert not log.with_name(log.name + ".3.gz").exists()
    assert tuner.observe(item("postgres_log", small)).state == "in-force"
    assert tuner.apply(["postgres_log"])[0].startswith("postgres_log: nothing to do")
    assert "kept in" in tuner.undo("postgres_log")[0]


# ------------------------------------------------------------------------ Ollama's own record

LOG = "\n".join(
    [
        'time=2026-10-04T09:00:00.000-04:00 level=INFO msg="starting llama-server" cmd="/x/llama-server'
        ' --model /m/blobs/sha256-aaaa1111 --port 1 -c 8192 -np 1"',
        '[GIN] 2026/10/04 - 09:00:05 | 200 | 1s | 127.0.0.1 | POST "/api/chat"',
        'time=2026-10-05T01:00:00.000-04:00 level=INFO msg="starting llama-server" cmd="/x/llama-server'
        ' --model /m/blobs/sha256-aaaa1111 --port 2 -c 65536 -np 1"',
        'time=2026-10-05T02:00:00.000-04:00 level=INFO msg="starting llama-server" cmd="/x/llama-server'
        ' --model /m/blobs/sha256-bbbb2222 --port 3 -c 4096 -np 1"',
        'time=not-a-time level=INFO msg="starting llama-server" cmd="/x/llama-server --model /m/sha256-cc -c 1"',
    ]
)


def write_log(home: Path, text: str = LOG) -> None:
    logs = home / ".ollama/logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "server.log").write_text(text + "\n")


def test_the_load_log_parses_each_load_with_its_blob_and_context() -> None:
    loads = ht.OllamaLoadLog.loads(LOG.splitlines())
    assert [(load.digest, load.num_ctx) for load in loads] == [
        ("aaaa1111", 8192),
        ("aaaa1111", 65536),
        ("bbbb2222", 4096),
    ]
    assert loads[0].at.isoformat() == "2026-10-04T13:00:00+00:00"


def test_reloads_in_the_trailing_window_against_the_declared_ceiling(tmp_path: Path) -> None:
    c = ctx(tmp_path)
    tuner = ht.HostTuner(SETTINGS, c)
    assert tuner.observe(item("ollama_fixed_num_ctx")).state == "absent"
    write_log(c.home)
    seen = tuner.observe(item("ollama_fixed_num_ctx"))
    assert seen.actual == {
        "loads": 3,
        "loads_per_day": 3.0,
        "distinct_num_ctx": 3,
        "window_hours": 24.0,
    }
    assert seen.state == "proposed"
    loose = settings_with(ollama_fixed_num_ctx={"max_distinct_num_ctx": 5})
    assert ht.HostTuner(loose, c).observe(item("ollama_fixed_num_ctx", loose)).state == "in-force"
    strict = settings_with(ollama_fixed_num_ctx={"max_distinct_num_ctx": 1, "adopted": True})
    tight = ht.HostTuner(strict, c)
    assert tight.observe(item("ollama_fixed_num_ctx", strict)).state == "drift"
    assert "not an environment setting" in tight.apply(["ollama_fixed_num_ctx"])[0]


def write_manifest(home: Path, name: str, tag: str, digest: str, size: int) -> None:
    path = home / ".ollama/models/manifests/registry.ollama.ai" / name / tag
    path.parent.mkdir(parents=True, exist_ok=True)
    layers = [
        {"mediaType": "application/vnd.ollama.image.template", "digest": "sha256:t", "size": 1},
        {
            "mediaType": "application/vnd.ollama.image.model",
            "digest": f"sha256:{digest}",
            "size": size,
        },
    ]
    path.write_text(json.dumps({"layers": layers}))


def test_models_are_listed_with_their_last_load_and_never_removed(tmp_path: Path) -> None:
    c = ctx(tmp_path)
    tuner = ht.HostTuner(settings_with(unused_models={"operator_approved": "listing"}), c)
    assert tuner.observe(item("unused_models")).state == "absent"
    write_log(c.home)
    write_manifest(c.home, "library/gpt-oss", "20b", "aaaa1111", 13_000_000_000)
    write_manifest(c.home, "someone/tiny", "latest", "dddd4444", 1_000_000_000)
    (c.home / ".ollama/models/manifests/registry.ollama.ai/library/broken").mkdir(parents=True)
    (c.home / ".ollama/models/manifests/registry.ollama.ai/library/broken/x").write_text("{")
    (c.home / ".ollama/models/manifests/stray").write_text("ignored: not name/tag deep")
    seen = tuner.observe(item("unused_models"))
    assert seen.state == "listed"
    assert [m["model"] for m in seen.actual] == ["gpt-oss:20b", "someone/tiny:latest"]
    assert seen.actual[0]["last_loaded"] == "2026-10-05T05:00:00Z"
    assert (
        "someone/tiny:latest (1.0 GB)" in seen.detail
        and "gpt-oss" not in seen.detail.split(":", 1)[1]
    )
    lines = tuner.apply(["unused_models"])
    assert lines[1].strip().startswith("ollama rm someone/tiny:latest")
    assert not any(call[:1] == ["ollama"] for call in c.runner.calls)


def test_with_every_model_recent_there_is_nothing_to_list(tmp_path: Path) -> None:
    c = ctx(tmp_path)
    write_log(c.home)
    write_manifest(c.home, "library/gpt-oss", "20b", "aaaa1111", 13_000_000_000)
    tuner = ht.HostTuner(settings_with(unused_models={"operator_approved": "x"}), c)
    assert tuner.apply(["unused_models"]) == ["unused_models: every model was loaded recently"]


# ------------------------------------------------------------------------ tuner and journal


def test_the_tuner_reports_gates_unknown_items_and_crashes(tmp_path: Path) -> None:
    c = ctx(tmp_path, {("launchctl",): ok("", 1)})
    tuner = ht.HostTuner(SETTINGS, c)
    lines = tuner.apply(["ollama_keep_alive", "docker_memory_cap"])
    assert lines[0].startswith("ollama_keep_alive: not applied: class B: waits")
    assert lines[1].startswith("docker_memory_cap: not applied: class C")
    with pytest.raises(KeyError, match="not_an_item"):
        tuner.apply(["not_an_item"])
    broken = settings_with(postgres_log={"max_mib": "lots"})
    log = c.path("/opt/homebrew/var/log/postgresql@18.log")
    log.parent.mkdir(parents=True)
    log.write_text("x")
    seen = ht.HostTuner(broken, c).observe(item("postgres_log", broken))
    assert seen.state == "unknown" and "could not observe" in seen.detail
    kinds = {o.kind for o in tuner.check(["log", "postgres"])}
    assert kinds == {"log", "postgres"}


def test_the_journal_is_append_only_and_says_where_a_bad_line_is(tmp_path: Path) -> None:
    journal = ht.TuningJournal(tmp_path / "j" / "journal.jsonl")
    assert journal.entries() == [] and journal.last("k", ("apply",)) is None
    journal.append(
        {"key": "k", "action": "apply", "kind": "env", "service": "s", "name": "A", "value": "1"}
    )
    journal.append({"key": "k", "action": "undo", "kind": "env", "service": "s", "name": "A"})
    journal.append({"key": "z", "action": "apply", "kind": "log"})
    assert [e["action"] for e in journal.entries()] == ["apply", "undo", "apply"]
    assert journal.applied_env("s") == {}
    journal.path.write_text(journal.path.read_text() + "\n{broken\n")
    with pytest.raises(ValueError, match="journal.jsonl:5"):
        journal.entries()


def test_ps_rows_and_flags() -> None:
    rows = ht.ServiceProcesses.parse("Mon Oct  5 06:40:00 2026 /x/ollama serve\nshort line\n")
    assert len(rows) == 1 and rows[0][1] == "/x/ollama serve" and rows[0][0] is not None
    assert ht.Clockwork.lstart("Someday") is None
    assert ht.ServiceProcesses.flag("a --flash-attn", "--flash-attn") == ""
    assert ht.ServiceProcesses.flag("a -np 2 -c 9", "-np") == "2"
    assert ht.ServiceProcesses.flag("a", "-np") is None


def test_context_paths_and_commands(tmp_path: Path) -> None:
    c = ctx(tmp_path)
    assert c.path("~/x") == c.home / "x" and c.path("/etc/x") == c.root / "etc/x"
    assert c.path("rel") == Path("rel")
    assert c.argv(["du", "-sk", "~/.cache/uv"]) == ["du", "-sk", str(c.home / ".cache/uv")]
    assert c.mac and not ctx(tmp_path, system="Linux").mac


# ------------------------------------------------------------------------ the weekly probes


class FixedClock:
    def now(self) -> str:
        return NOW


def probe_ctx(
    tmp_path: Path, system: str, answers: Mapping[tuple[str, ...], Any] | None = None
) -> hh.ProbeContext:
    home, root = tmp_path / "home", tmp_path / "root"
    home.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    return hh.ProbeContext(
        HEALTH,
        FakeRunner(answers),
        ms.FigureFactory(FixedClock(), "sha256:test"),
        system,
        root=root,
        home=home,
        wall=lambda: NOW_EPOCH,
        which=lambda name: None,
    )


def by_id(figures: Sequence[ms.Figure]) -> dict[str, ms.Figure]:
    return {f.id: f for f in figures}


def test_model_loads_per_day_and_distinct_contexts(tmp_path: Path) -> None:
    pc = probe_ctx(tmp_path, "Darwin")
    skipped = by_id(hh.ModelLoadProbe(pc).run())
    assert all(f.status == "skipped" for f in skipped.values())
    write_log(pc.home)
    figures = by_id(hh.ModelLoadProbe(pc).run())
    assert figures["ollama.loads_per_day"].value == round(3 / 7, 1)
    assert figures["ollama.distinct_num_ctx"].value == 3
    assert figures["ollama.loads_by_day"].value == {"2026-10-04": 1, "2026-10-05": 2}


TOP = """Processes: 438 total
Disks: 117080534/4949G read, 52283066/2095G written.

PID    COMMAND          MEM   CMPRS
84130  llama-server     17G   3738M
957    com.docker.sailo 8649M 8063M
42988  Code Helper (Plu 1972M- 1969M
44038  mystery          809K  0B
12     broken           lots  0B
"""
VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Swapouts:                                   96834411.
"""


def test_the_macos_budget_and_the_share_of_writes_that_is_swap(tmp_path: Path) -> None:
    answers = {
        ("top",): ok(TOP),
        ("sysctl", "-n", "kern.boottime"): ok(
            f"{{ sec = {int(NOW_EPOCH - 100 * 3600)}, usec = 0 }}"
        ),
        ("vm_stat",): ok(VM_STAT),
    }
    figures = by_id(hh.ProcessBudgetProbe(probe_ctx(tmp_path, "Darwin", answers)).run())
    budget = figures["memory.budget"].value
    assert list(budget) == ["ollama", "docker", "ide", "other"]
    assert budget["ollama"] == {"processes": 1, "mem_gib": 17.0, "compressed_gib": 3.65}
    assert budget["ide"]["mem_gib"] == round(1972 / 1024, 2)
    written = 2095 * 1024**3
    assert figures["storage.host_writes_gb_per_hour_since_boot"].value == round(
        written / 1e9 / 100, 1
    )
    assert figures["memory.swap_share_of_writes"].value == round(96834411 * 16384 / written, 2)


def test_the_budget_says_why_when_it_cannot_measure(tmp_path: Path) -> None:
    figures = by_id(hh.ProcessBudgetProbe(probe_ctx(tmp_path, "Darwin")).run())
    assert figures["memory.budget"].status == "skipped"
    assert figures["storage.host_writes_gb_per_hour_since_boot"].status == "skipped"
    answers = {
        ("top",): ok(TOP),
        ("sysctl",): ok("{ sec = 1, usec = 0 }"),
        ("vm_stat",): ok("nothing"),
    }
    figures = by_id(hh.ProcessBudgetProbe(probe_ctx(tmp_path, "Darwin", answers)).run())
    assert figures["memory.swap_share_of_writes"].reason == "no swap-out counter"


def test_the_linux_budget(tmp_path: Path) -> None:
    pc = probe_ctx(
        tmp_path,
        "Linux",
        {("ps",): ok("  2048 postgres\n 10240 llama-server\n  junk\n"), ("getconf",): ok("4096\n")},
    )
    proc = pc.root / "proc"
    proc.mkdir()
    (proc / "diskstats").write_text(
        " 259 0 nvme0n1 1 2 3 4 5 6 100 8 9\n 259 1 nvme0n1p1 1 2 3 4 5 6 50 8 9\n"
    )
    (proc / "uptime").write_text("7200.0 100.0\n")
    (proc / "vmstat").write_text("pswpout 25\n")
    figures = by_id(hh.ProcessBudgetProbe(pc).run())
    assert figures["memory.budget"].value["ollama"]["compressed_gib"] is None
    assert (
        figures["storage.host_writes_gb_per_hour_since_boot"].conditions["bytes_written_since_boot"]
        == 51200
    )
    assert figures["memory.swap_share_of_writes"].value == round(25 * 4096 / 51200, 2)
    empty = by_id(hh.ProcessBudgetProbe(probe_ctx(tmp_path / "e", "Linux")).run())
    assert empty["memory.budget"].status == "skipped"
    assert empty["memory.swap_share_of_writes"].status == "skipped"


def test_the_tuning_probe_records_what_was_in_force(tmp_path: Path) -> None:
    pc = probe_ctx(tmp_path, "Darwin", {("launchctl",): ok("", 1), ("psql",): ok("128MB\n")})
    figures = by_id(hh.TuningProbe(pc, REPO / "scripts/host_tuning.toml").run())
    state = figures["tuning.state"].value
    assert state["postgres_shared_buffers"]["state"] == "in-force"
    assert state["ollama_kv_cache_type"] == {
        "class": "B",
        "state": "proposed",
        "declared": "q8_0",
        "actual": None,
    }
    assert "uv_cache" not in state, "a reclaim is sized when applied, not weekly"
    assert figures["tuning.attention"].value == 0


# ------------------------------------------------------------------------ the command


def cli(tmp_path: Path, answers: Mapping[tuple[str, ...], Any] | None = None) -> hh.HostHealthCli:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return hh.HostHealthCli(
        REPO,
        FixedClock(),
        FakeRunner(answers),
        home=home,
        which=lambda name: None,
        system="Darwin",
        root=tmp_path / "root",
        describer=None,
        environ={},
    )


def test_tune_check_plan_apply_and_undo_from_the_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "root").mkdir()
    command = cli(tmp_path, {("launchctl",): ok("", 1), ("psql",): ok("128MB\n")})
    assert command.run(["tune", "check"]) == 0
    out = capsys.readouterr().out
    assert "proposed        B ollama_kv_cache_type" in out
    assert command.run(["tune", "check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["key"] == "ollama_max_loaded_models"
    assert command.run(["tune", "plan", "--only", "ollama_keep_alive"]) == 0
    assert "not applied: class B" in capsys.readouterr().out
    assert command.run(["tune", "undo"]) == 2
    assert command.run(["tune", "undo", "ollama_keep_alive"]) == 0
    assert "nothing to undo" in capsys.readouterr().out
    assert command.run(["tune", "apply", "--only", "nope"]) == 2
    assert "not declared" in capsys.readouterr().err


def test_tune_check_fails_when_an_allowed_item_is_not_in_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "root/opt/homebrew/var/log/postgresql@18.log"
    log.parent.mkdir(parents=True)
    log.write_bytes(b"x" * (65 * ht.MIB))
    assert cli(tmp_path).run(["tune", "check"]) == 1
    assert "postgres_log" in capsys.readouterr().err
