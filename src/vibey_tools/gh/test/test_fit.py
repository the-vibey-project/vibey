# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The fit calculus (#263): both sides measured, the projection stated, the floor loud."""

from __future__ import annotations

import json

import pytest

from vibey_gh import fit
from vibey_gh.cli import main
from vibey_gh.fit import (
    ADMIT,
    DEFAULT_OLLAMA_URL,
    DEFER,
    FLOOR,
    OLLAMA_URL_ENV,
    ContextSizer,
    DarwinMemorySampler,
    Estimate,
    LinuxMemorySampler,
    Machine,
    Model,
    Observation,
    OllamaModelSampler,
    TextFileReader,
    decide,
    estimate_from,
    headroom_gb,
    machine_sampler,
    sample_machine,
    sample_model,
    saturating_wait,
)
from vibey_gh.fitloop import JOURNAL_ENV
from vibey_gh.interfaces.context_sizer_interface import ContextSizerInterface

MACHINE = Machine(total_gb=25.77, free_gb=2.97, swap_used_gb=6.5, swap_total_gb=7.0)
MODEL = Model(name="qwen2.5-coder:14b", size_gb=10.52, context_length=9390)


@pytest.fixture(autouse=True)
def _journal_stays_in_the_test(monkeypatch, tmp_path):
    """`vibey-gh fit` journals by default, to a file in the user's home. No test may
    reach it."""
    monkeypatch.setenv(JOURNAL_ENV, str(tmp_path / "default-journal.jsonl"))


def test_available_is_free_memory_plus_unspoken_paging_space():
    assert MACHINE.available_gb == 3.47
    # Over-committed swap never reports negative headroom.
    tight = Machine(total_gb=8.0, free_gb=0.5, swap_used_gb=9.0, swap_total_gb=4.0)
    assert tight.available_gb == 0.5


def test_service_time_scales_with_payload_size():
    est = Estimate(slots=3.1, base_s=40.0, rate_s_per_kb=7.5, samples=6)
    assert est.service_s(0) == 40.0
    assert est.service_s(10240) == 115.0  # 40 + 7.5 * 10 KB


def test_an_estimate_without_evidence_says_so():
    est = estimate_from([])
    assert est.samples == 0 and est.slots == 1.0
    assert est.base_s == 0.0 and est.rate_s_per_kb == 0.0


def test_one_payload_size_cannot_separate_base_from_rate():
    """Two unknowns, one distinct x: the honest fit puts it all in base and leaves
    the rate at zero rather than inventing a slope."""
    obs = [Observation(payload_bytes=8192, elapsed_s=t, concurrent=2) for t in (100.0, 120.0)]
    est = estimate_from(obs)
    assert est.rate_s_per_kb == 0.0
    assert est.base_s == 110.0


def test_varied_payloads_recover_base_and_rate():
    obs = [
        Observation(payload_bytes=1024, elapsed_s=60.0, concurrent=6),
        Observation(payload_bytes=11264, elapsed_s=160.0, concurrent=6),
    ]
    est = estimate_from(obs)
    assert est.rate_s_per_kb == pytest.approx(10.0, abs=0.01)
    assert est.base_s == pytest.approx(50.0, abs=0.5)
    assert est.slots == 2.0  # bounded by the sample count, never invented


def test_a_physically_meaningless_fit_falls_back_to_the_mean():
    """A negative slope would predict big payloads finishing sooner; refuse it."""
    obs = [
        Observation(payload_bytes=1024, elapsed_s=200.0, concurrent=2),
        Observation(payload_bytes=20480, elapsed_s=100.0, concurrent=2),
    ]
    est = estimate_from(obs)
    assert est.rate_s_per_kb == 0.0
    assert est.base_s == 150.0


def test_headroom_wants_the_model_plus_a_share_per_slot():
    assert headroom_gb(MACHINE, MODEL, slots=1.0) == 7.05
    assert headroom_gb(MACHINE, MODEL, slots=4.0) > 7.05
    roomy = Machine(total_gb=128.0, free_gb=90.0, swap_used_gb=0.0, swap_total_gb=8.0)
    assert headroom_gb(roomy, MODEL, slots=4.0) == 0.0


def test_an_unreadable_model_is_the_floor_not_a_guess():
    verdict = decide(
        MACHINE, None, estimate_from([]), queue_depth=0, payload_bytes=1024, deadline_s=900
    )
    assert verdict.verdict == FLOOR and not verdict.ok
    assert "forbids proceeding on an assumed model" in verdict.reason


def test_a_model_beyond_the_machine_fails_loudly_with_the_numbers():
    tiny = Machine(total_gb=8.0, free_gb=2.0, swap_used_gb=1.0, swap_total_gb=2.0)
    huge = Model(name="giant:400b", size_gb=240.0, context_length=128000)
    verdict = decide(
        tiny, huge, estimate_from([]), queue_depth=0, payload_bytes=1024, deadline_s=900
    )
    assert verdict.verdict == FLOOR
    assert "240.0 GB" in verdict.reason and "absolute ceiling" in verdict.reason
    assert verdict.headroom_gb == 230.0


def test_work_that_cannot_meet_the_deadline_defers_with_the_arithmetic():
    est = Estimate(slots=2.0, base_s=100.0, rate_s_per_kb=10.0, samples=8)
    verdict = decide(MACHINE, MODEL, est, queue_depth=40, payload_bytes=10240, deadline_s=300)
    assert verdict.verdict == DEFER and not verdict.ok
    assert "exceeds the 300" in verdict.reason
    assert verdict.projected_wait_s > 0 and verdict.projected_service_s == 200.0


def test_work_that_fits_is_admitted_and_still_reports_headroom():
    est = Estimate(slots=4.0, base_s=50.0, rate_s_per_kb=5.0, samples=12)
    verdict = decide(MACHINE, MODEL, est, queue_depth=2, payload_bytes=4096, deadline_s=900)
    assert verdict.verdict == ADMIT and verdict.ok
    assert "fits the 900" in verdict.reason
    # Headroom is reported even on admit: the projection wants more than exists here.
    assert verdict.headroom_gb > 0
    assert any("grow paging space" in n for n in verdict.notes)


def test_an_unmeasured_projection_says_it_is_a_floor_not_a_forecast():
    verdict = decide(
        MACHINE, MODEL, estimate_from([]), queue_depth=0, payload_bytes=1024, deadline_s=900
    )
    assert any("τ is unmeasured" in n for n in verdict.notes)


def test_sample_machine_reads_the_real_shapes(monkeypatch):
    def fake(*cmd: str) -> str:
        if "hw.memsize" in cmd:
            return "25769803776\n"
        if "vm.swapusage" in cmd:
            return "total = 7168.00M  used = 6651.12M  free = 516.88M  (encrypted)\n"
        if cmd[0] == "vm_stat":
            return (
                "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
                "Pages free:                    100000.\n"
                "Pages active:                  400000.\n"
                "Pages inactive:                 80000.\n"
                "Pages wired down:              200000.\n"
                "Pages occupied by compressor:  120000.\n"
            )
        return ""

    monkeypatch.setattr(fit, "_run", fake)
    machine = sample_machine(platform_name="darwin")
    assert machine.total_gb == 25.77
    assert machine.free_gb == pytest.approx(2.95, abs=0.05)
    assert machine.swap_total_gb == 7.0 and machine.swap_used_gb == pytest.approx(6.5, abs=0.01)


def test_sample_machine_reports_zero_rather_than_guessing(monkeypatch):
    monkeypatch.setattr(fit, "_run", lambda *cmd: "")
    machine = sample_machine(platform_name="darwin")
    assert machine.total_gb == 0.0 and machine.free_gb == 0.0
    # Zero is the absence of a measurement, and says so rather than passing for
    # a machine with room for nothing.
    assert not machine.readable


def test_sample_model_reads_the_runner(monkeypatch):
    monkeypatch.setattr(fit.shutil, "which", lambda _: "/usr/bin/curl")
    monkeypatch.setattr(
        fit,
        "_run",
        lambda *cmd: (
            '{"models": [{"name": "qwen2.5-coder:14b", "size": 10520000000,'
            ' "context_length": 9390}]}'
        ),
    )
    model = sample_model("qwen2.5-coder:14b")
    assert model is not None and model.size_gb == 10.52 and model.context_length == 9390
    assert sample_model("not-loaded") is None


@pytest.mark.parametrize(
    "which, body",
    [
        (None, ""),
        ("/usr/bin/curl", ""),
        ("/usr/bin/curl", "not json"),
        ("/usr/bin/curl", '{"models": ["a bare string", {"name": "other"}]}'),
    ],
)
def test_an_unreadable_runner_yields_no_model(monkeypatch, which, body):
    monkeypatch.setattr(fit.shutil, "which", lambda _: which)
    monkeypatch.setattr(fit, "_run", lambda *cmd: body)
    assert sample_model("qwen2.5-coder:14b") is None


def test_run_survives_a_missing_or_hanging_command(monkeypatch):
    def boom(*a, **k):
        raise OSError("no such tool")

    monkeypatch.setattr(fit.subprocess, "run", boom)
    assert fit._run("nope") == ""

    class Failed:
        returncode = 1
        stdout = "ignored"

    monkeypatch.setattr(fit.subprocess, "run", lambda *a, **k: Failed())
    assert fit._run("false") == ""


def test_fit_cli_reports_both_sides(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fit, "sample_machine", lambda: MACHINE)
    monkeypatch.setattr(fit, "sample_model", lambda name, base_url=...: MODEL)
    assert main(["fit"]) == 0
    out = capsys.readouterr().out
    assert "25.77 GB total" in out and "qwen2.5-coder:14b 10.52 GB" in out
    assert "ADMIT" in out and "headroom wanted" in out

    monkeypatch.setattr(fit, "sample_model", lambda name, base_url=...: None)
    assert main(["fit"]) == 1
    assert "could not be read from the runner" in capsys.readouterr().out


def test_a_page_size_line_without_digits_falls_back_to_the_default(monkeypatch):
    """vm_stat's header is not contractual; an unparseable one uses 4096 rather
    than crashing or inventing a size."""
    monkeypatch.setattr(
        fit,
        "_run",
        lambda *cmd: (
            "Mach Virtual Memory Statistics:\nPages free: 100000.\n" if cmd[0] == "vm_stat" else ""
        ),
    )
    machine = sample_machine(platform_name="darwin")
    assert machine.free_gb == pytest.approx(0.41, abs=0.01)  # 100000 * 4096 bytes


def test_a_comfortable_machine_reports_no_headroom_note():
    roomy = Machine(total_gb=128.0, free_gb=90.0, swap_used_gb=0.0, swap_total_gb=16.0)
    est = Estimate(slots=4.0, base_s=50.0, rate_s_per_kb=5.0, samples=12)
    verdict = decide(roomy, MODEL, est, queue_depth=1, payload_bytes=4096, deadline_s=900)
    assert verdict.verdict == ADMIT
    assert verdict.headroom_gb == 0.0
    assert not any("grow paging space" in n for n in verdict.notes)


def test_wait_is_superlinear_because_the_measurements_said_so():
    """The stress escalation falsified this module's original linear wait one rung
    after it shipped: 22 s/job through N=12, then 59 s/job by N=16. Slack stays
    nearly linear; saturation goes quadratic."""
    # Idle runner: no queue, no wait, whatever the slot count.
    assert saturating_wait(100.0, queue_depth=0, slots=4.0) == 0.0
    # Slack (rho < 1): close to the linear estimate.
    assert saturating_wait(100.0, queue_depth=2, slots=4.0) == pytest.approx(75.0)
    # Saturated (rho = 4): four times the linear projection, matching the observed
    # slope growth rather than a line.
    linear = 100.0 * (16 / 4)
    assert saturating_wait(100.0, queue_depth=16, slots=4.0) == pytest.approx(5 * linear)
    # A runner with no slots cannot be projected onto.
    assert saturating_wait(100.0, queue_depth=8, slots=0.0) == 0.0


def test_the_superlinear_wait_defers_work_a_linear_model_would_have_admitted():
    """The concrete regression: at sixteen deep on four slots the linear model
    projected 400 s and would have admitted against a 900 s deadline; the measured
    behaviour is far worse, and the corrected rule defers."""
    est = Estimate(slots=4.0, base_s=100.0, rate_s_per_kb=0.0, samples=16)
    verdict = decide(MACHINE, MODEL, est, queue_depth=16, payload_bytes=1024, deadline_s=900)
    assert verdict.verdict == DEFER
    assert verdict.projected_wait_s == pytest.approx(2000.0)


# -- the machine side on Linux ------------------------------------------------------
#
# This machine is macOS, and CI runs the suite on Linux, so neither platform's sampler
# may depend on the platform running the test. Every reading below is handed to the
# sampler through its injected `TextFileReaderInterface` (sub-doctrine 9.b): exact file
# contents, no module attribute patched, the same assertions on either kind of machine.

HOST_MEMINFO = """MemTotal:       32793692 kB
MemFree:         1000000 kB
MemAvailable:    8000000 kB
SwapTotal:       2097152 kB
SwapFree:        1048576 kB
Hugepagesize:       2048 kB
a line with no colon at all
"""

V2_LIMIT, V1_LIMIT = fit.LINUX_CGROUP_MEMORY_LIMIT_PATHS
V2_USAGE, V1_USAGE = fit.LINUX_CGROUP_MEMORY_USAGE_PATHS
(V2_SWAP_LIMIT,) = fit.LINUX_CGROUP_SWAP_LIMIT_PATHS
(V2_SWAP_USAGE,) = fit.LINUX_CGROUP_SWAP_USAGE_PATHS


class FakeFiles:
    """The read seam, given exact contents. A file not in the mapping does not exist."""

    def __init__(self, files: dict[str, str]):
        self.files = files

    def read(self, path: str) -> str | None:
        return self.files.get(path)


def linux(**files: str) -> Machine:
    return LinuxMemorySampler(FakeFiles({fit.LINUX_MEMINFO_PATH: HOST_MEMINFO, **files})).sample()


def test_the_sampler_is_the_one_that_can_read_this_kind_of_machine():
    assert isinstance(machine_sampler("linux"), LinuxMemorySampler)
    assert isinstance(machine_sampler("linux2"), LinuxMemorySampler)
    assert isinstance(machine_sampler("darwin"), DarwinMemorySampler)
    # No argument means this interpreter's own platform, whichever that is.
    assert isinstance(machine_sampler(), (LinuxMemorySampler, DarwinMemorySampler))


def test_linux_reads_its_memory_from_proc_meminfo():
    """The defect: on Linux `sysctl` and `vm_stat` do not exist, so every field read as
    zero and the machine silently looked empty."""
    machine = LinuxMemorySampler(FakeFiles({fit.LINUX_MEMINFO_PATH: HOST_MEMINFO})).sample()
    assert machine.readable
    assert machine.total_gb == 33.58  # 32793692 kB
    assert machine.free_gb == 8.19  # MemAvailable, not MemFree
    assert machine.swap_total_gb == 2.15
    assert machine.swap_used_gb == 1.07  # SwapTotal - SwapFree


def test_meminfo_without_memavailable_falls_back_to_memfree():
    """MemAvailable arrived in Linux 3.14; an older kernel still has to be read."""
    machine = LinuxMemorySampler(
        FakeFiles({fit.LINUX_MEMINFO_PATH: "MemTotal: 4000000 kB\nMemFree: 2000000 kB\n"})
    ).sample()
    assert machine.total_gb == 4.1 and machine.free_gb == 2.05


def test_meminfo_lines_that_state_no_usable_number_are_skipped():
    """`/proc/meminfo` is not contractual: a key with no value, a non-numeric value, and
    a value with no unit all have to survive being read."""
    machine = LinuxMemorySampler(
        FakeFiles(
            {
                fit.LINUX_MEMINFO_PATH: (
                    "MemTotal:\nMemAvailable: not-a-number kB\nMemFree: 2048\nSwapTotal: 0 kB\n"
                )
            }
        )
    ).sample()
    assert machine.total_gb == 0.0 and not machine.readable
    assert machine.free_gb == 0.0  # 2048 bytes, unit-less, rounds to 0.00 GB


def test_inside_a_container_the_cgroup_limit_wins_over_the_hosts_memory():
    """`/proc/meminfo` is the HOST's memory inside a container: this process is killed at
    the cgroup limit long before it reaches the host's total, so projecting on the host's
    numbers admits work the container cannot run."""
    machine = linux(
        **{
            V2_LIMIT: "4294967296\n",
            V2_USAGE: "1073741824\n",
            V2_SWAP_LIMIT: "536870912\n",
            V2_SWAP_USAGE: "268435456\n",
        }
    )
    assert machine.readable
    assert machine.total_gb == 4.29  # the cgroup's 4 GiB, not the host's 32 GB
    assert machine.free_gb == 3.22  # limit - current
    assert machine.swap_total_gb == 0.54 and machine.swap_used_gb == 0.27


def test_a_cgroup_v1_limit_is_read_when_v2_says_max():
    """v2 spells "no limit" as the word `max`; the v1 file is then the one to read."""
    machine = linux(**{V2_LIMIT: "max\n", V1_LIMIT: "4294967296\n", V1_USAGE: "2147483648\n"})
    assert machine.total_gb == 4.29 and machine.free_gb == 2.15


def test_a_container_below_the_hierarchy_root_is_read_where_its_limit_lives():
    """The ROOT files are not this process's files when it sits in a nested cgroup.

    On a host-mounted hierarchy -- Docker, Kubernetes -- `/sys/fs/cgroup/memory.max`
    reads `max` while the container's own `memory.max`, under the path
    `/proc/self/cgroup` reports, holds the real ceiling. Reading only the root falls
    through to `/proc/meminfo` and projects on the HOST's memory, which is the exact
    mistake preferring the cgroup exists to avoid.
    """
    machine = linux(
        **{
            "/proc/self/cgroup": "0::/docker/abc123\n",
            V2_LIMIT: "max\n",  # the root says "no limit", as it does in a container
            "/sys/fs/cgroup/docker/abc123/memory.max": "4294967296\n",
            "/sys/fs/cgroup/docker/abc123/memory.current": "1073741824\n",
        }
    )
    assert machine.total_gb == 4.29  # the container's 4 GiB, not the host's 32 GB
    assert machine.free_gb == 3.22  # limit - current, both read from the SAME cgroup


def test_a_cgroup_v1_memory_controller_names_its_own_path():
    """v1 writes one line per controller, and the memory line is the one that governs a
    memory limit -- a sibling controller can sit at a different path entirely."""
    machine = linux(
        **{
            "/proc/self/cgroup": "5:cpu,cpuacct:/elsewhere\n4:memory:/docker/xyz\n",
            V1_LIMIT: "max\n",
            "/sys/fs/cgroup/memory/docker/xyz/memory.limit_in_bytes": "2147483648\n",
            "/sys/fs/cgroup/memory/docker/xyz/memory.usage_in_bytes": "1073741824\n",
        }
    )
    assert machine.total_gb == 2.15 and machine.free_gb == 1.07


@pytest.mark.parametrize(
    "contents",
    [
        "0::/\n",  # already at the root: nothing to add
        "",  # an empty file
        "garbage without enough colons\n",  # nothing parseable
    ],
)
def test_a_process_at_the_root_reads_exactly_the_configured_paths(contents: str):
    """Deriving nothing must leave the configured paths untouched, so a plain host and a
    caller that mounts its hierarchy elsewhere both behave exactly as before."""
    machine = linux(**{"/proc/self/cgroup": contents, V2_LIMIT: "4294967296\n"})
    assert machine.total_gb == 4.29


def test_an_unreadable_proc_self_cgroup_changes_nothing():
    """The file is absent on anything that is not Linux-with-cgroups, and its absence is
    not a reason to stop reading the hierarchy roots."""
    machine = linux(**{V2_LIMIT: "4294967296\n"})
    assert machine.total_gb == 4.29


def test_a_cgroup_ceiling_at_or_above_the_host_is_not_a_ceiling():
    """v1 spells "no limit" as a sentinel near 2**63. A limit that large is not a limit,
    and the host's own numbers stand."""
    machine = linux(**{V1_LIMIT: "9223372036854771712\n"})
    assert machine.total_gb == 33.58 and machine.free_gb == 8.19
    assert machine.swap_total_gb == 2.15  # still the host's paging space


def test_a_cgroup_limit_without_a_usage_reading_reports_no_free_memory():
    """No `memory.current` to subtract, so free memory inside this cgroup was never
    measured. Unmeasured is zero: the host's MemAvailable describes the host's accounting
    scope, and capping it at the limit would say a full 4 GiB container has 4 GiB free."""
    machine = linux(**{V2_LIMIT: "4294967296\n"})
    assert machine.total_gb == 4.29 and machine.free_gb == 0.0
    # The host's swap is not this container's to claim.
    assert machine.swap_total_gb == 0.0 and machine.swap_used_gb == 0.0


def test_a_hybrid_host_reads_usage_from_the_same_cgroup_version_as_the_limit():
    """Both hierarchies mounted, v2 states the limit, v2's `memory.current` is unreadable
    and v1's `memory.usage_in_bytes` is not. Subtracting the v1 figure from the v2 limit
    mixes two accounting scopes and overstates free memory, so it is not done."""
    machine = linux(**{V2_LIMIT: "4294967296\n", V1_USAGE: "1073741824\n"})
    assert machine.total_gb == 4.29 and machine.free_gb == 0.0


def test_a_usage_file_that_states_no_number_is_no_reading_at_all():
    """`memory.current` reads `max` on a cgroup with no memory accounting; that is not a
    usage figure, and inventing one from it would be a guess."""
    machine = linux(**{V2_LIMIT: "4294967296\n", V2_USAGE: "max\n"})
    assert machine.total_gb == 4.29 and machine.free_gb == 0.0


def test_an_override_that_leaves_no_usage_path_for_this_hierarchy_reads_none():
    """A caller may override one path tuple and not the other (ADR-0018 keeps both keys):
    a hierarchy with no usage file at the limit's index simply states no usage."""
    machine = LinuxMemorySampler(
        FakeFiles({fit.LINUX_MEMINFO_PATH: HOST_MEMINFO, V2_LIMIT: "4294967296\n"}),
        cgroup_usage_paths=(),
    ).sample()
    assert machine.total_gb == 4.29 and machine.free_gb == 0.0


def test_a_cgroup_limit_is_read_even_when_proc_meminfo_is_not():
    machine = LinuxMemorySampler(FakeFiles({V2_LIMIT: "2147483648\n"})).sample()
    assert machine.readable and machine.total_gb == 2.15
    assert machine.free_gb == 0.0  # unknown, and unknown is not "all of it"


def test_a_linux_machine_that_states_nothing_is_the_floor_not_an_empty_machine():
    machine = LinuxMemorySampler(FakeFiles({})).sample()
    assert not machine.readable
    assert machine.total_gb == 0.0 and machine.free_gb == 0.0
    assert machine.swap_total_gb == 0.0 and machine.swap_used_gb == 0.0


def test_the_default_reader_is_the_real_filesystem(tmp_path):
    """No reader injected: the sampler reads real files, and a file that is not there is
    `None` rather than an exception."""
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 1000000 kB\nMemAvailable: 500000 kB\n", encoding="utf-8")
    machine = LinuxMemorySampler(
        meminfo_path=str(meminfo),
        cgroup_limit_paths=(str(tmp_path / "not-mounted"),),
    ).sample()
    assert machine.readable and machine.total_gb == 1.02 and machine.free_gb == 0.51
    assert TextFileReader().read(str(tmp_path / "not-mounted")) is None


def test_an_unreadable_machine_is_the_floor_not_a_projection():
    """The other half of doctrine 10's floor: a model that cannot be read is already a
    FLOOR, and so is a machine that cannot be read. Before this, an unreadable machine
    reported zero, skipped the ceiling check, and was quietly admitted."""
    unknown = Machine(
        total_gb=0.0, free_gb=0.0, swap_used_gb=0.0, swap_total_gb=0.0, readable=False
    )
    verdict = decide(
        unknown, MODEL, estimate_from([]), queue_depth=0, payload_bytes=1024, deadline_s=900
    )
    assert verdict.verdict == FLOOR and not verdict.ok
    assert "would not state its own memory" in verdict.reason


def test_the_fit_cli_says_out_loud_that_the_machine_could_not_be_read(
    monkeypatch, capsys, tmp_path
):
    monkeypatch.chdir(tmp_path)
    unknown = Machine(
        total_gb=0.0, free_gb=0.0, swap_used_gb=0.0, swap_total_gb=0.0, readable=False
    )
    monkeypatch.setattr(fit, "sample_machine", lambda: unknown)
    monkeypatch.setattr(fit, "sample_model", lambda name, base_url=...: MODEL)
    assert main(["fit"]) == 1
    out = capsys.readouterr().out
    assert "machine memory could not be read" in out
    assert "FLOOR" in out


# -- the model side, read from a runner that has not loaded it (#135) -------------------


def _runner(responses: dict[str, str], seen: list[tuple[str, ...]] | None = None):
    """A runner that answers each endpoint with a fixed body, and remembers every request."""

    def run(*cmd: str) -> str:
        if seen is not None:
            seen.append(cmd)
        return next((body for path, body in responses.items() if cmd[-1].endswith(path)), "")

    return run


def _sampler(responses: dict[str, str], seen: list[tuple[str, ...]] | None = None, **kw):
    return OllamaModelSampler(
        "http://runner:11434", environ={}, curl="/bin/curl", run=_runner(responses, seen), **kw
    )


_HELD = json.dumps({"models": [{"name": "qwen2.5-coder:14b", "size": 8988124069}]})


def test_a_model_held_but_not_loaded_is_read_from_its_metadata():
    """`/api/ps` lists only what is loaded, so before this a model the runner held on disk
    read exactly like one it did not have, and every cold call was refused at the floor.
    `/api/tags` confirms it is held; `/api/show` states its context; `resident` is false
    because its size is now the weights on disk rather than a resident measurement."""
    seen: list[tuple[str, ...]] = []
    sampler = _sampler(
        {
            "/api/ps": '{"models": []}',
            "/api/tags": _HELD,
            # The architecture's own key wins over any other `*.context_length`.
            "/api/show": json.dumps(
                {
                    "model_info": {
                        "general.architecture": "qwen2",
                        "llama.context_length": 4096,
                        "qwen2.context_length": 32768,
                    }
                }
            ),
        },
        seen,
    )
    model = sampler.sample("qwen2.5-coder:14b")
    assert model == Model(
        name="qwen2.5-coder:14b", size_gb=8.99, context_length=32768, resident=False
    )
    assert [cmd[-1] for cmd in seen] == [
        "http://runner:11434/api/ps",
        "http://runner:11434/api/tags",
        "http://runner:11434/api/show",
    ]
    show = seen[-1]
    body = json.loads(show[show.index("-d") + 1])
    assert body == {"model": "qwen2.5-coder:14b", "name": "qwen2.5-coder:14b"}
    assert seen[0][:4] == ("/bin/curl", "-s", "-m", "10")


def test_a_loaded_model_is_read_from_what_is_resident_and_nothing_else():
    seen: list[tuple[str, ...]] = []
    ps = json.dumps(
        {"models": [{"model": "qwen2.5-coder:14b", "size": 10520000000, "context_length": 9390}]}
    )
    model = _sampler({"/api/ps": ps}, seen).sample("qwen2.5-coder:14b")
    assert model == MODEL and model.resident
    assert len(seen) == 1


def test_a_model_the_runner_does_not_hold_is_none_and_its_metadata_is_never_asked_for():
    seen: list[tuple[str, ...]] = []
    sampler = _sampler({"/api/ps": '{"models": []}', "/api/tags": _HELD}, seen)
    assert sampler.sample("llama3:70b") is None
    assert not any(cmd[-1].endswith("/api/show") for cmd in seen)


@pytest.mark.parametrize("tags", ["", "not json", "[1, 2]", '{"models": null}'])
def test_a_runner_that_will_not_say_what_it_holds_yields_no_model(tags):
    """Presence unconfirmed is not presence: the floor, rather than a model assumed held."""
    assert _sampler({"/api/ps": '{"models": []}', "/api/tags": tags}).sample("m") is None


@pytest.mark.parametrize(
    "show, context",
    [
        ("", 0),
        ("[]", 0),
        ('{"model_info": "not a mapping"}', 0),
        ('{"model_info": {"general.architecture": "qwen2"}}', 0),
        ('{"model_info": {"x.context_length": "big", "y.context_length": true}}', 0),
        ('{"model_info": {"llama.context_length": 8192}}', 8192),
        (
            json.dumps(
                {
                    "model_info": {
                        "general.architecture": "qwen2",
                        "qwen2.context_length": 0,
                        "rope.context_length": 16384,
                    }
                }
            ),
            16384,
        ),
    ],
)
def test_metadata_that_states_no_usable_context_reads_as_zero(show, context):
    """A held model is still a model when its metadata is thin; zero is the absence of a
    context reading, exactly as a loaded model that states none reports it."""
    responses = {"/api/ps": '{"models": []}', "/api/tags": _HELD, "/api/show": show}
    model = _sampler(responses).sample("qwen2.5-coder:14b")
    assert model is not None and not model.resident
    assert model.context_length == context and model.size_gb == 8.99


@pytest.mark.parametrize(
    "asked, listed",
    [
        ("llama3", "llama3:latest"),
        ("registry.local:5000/team/llama3", "registry.local:5000/team/llama3:latest"),
    ],
)
def test_a_bare_name_is_the_latest_tag_as_the_runner_resolves_it(asked, listed):
    ps = json.dumps({"models": [{"name": listed, "size": 4.7e9, "context_length": 8192}]})
    model = _sampler({"/api/ps": ps}).sample(asked)
    assert model is not None and model.name == asked and model.size_gb == 4.7


def test_a_tagged_name_is_not_widened_to_latest():
    ps = json.dumps({"models": [{"name": "llama3:latest", "size": 4.7e9}]})
    responses = {"/api/ps": ps, "/api/tags": ps}
    assert _sampler(responses).sample("llama3:8b") is None


def test_the_request_timeout_is_a_setting_not_a_constant():
    seen: list[tuple[str, ...]] = []
    _sampler({}, seen, timeout_s=3).sample("m")
    assert seen[0][2:4] == ("-m", "3")


@pytest.mark.parametrize(
    "explicit, environ, fallback, expected",
    [
        ("http://flag:1/", {OLLAMA_URL_ENV: "http://env:2"}, DEFAULT_OLLAMA_URL, "http://flag:1"),
        (None, {OLLAMA_URL_ENV: "http://env:2/"}, DEFAULT_OLLAMA_URL, "http://env:2"),
        ("", {OLLAMA_URL_ENV: ""}, DEFAULT_OLLAMA_URL, "http://127.0.0.1:11434"),
        (None, {}, "http://configured:3", "http://configured:3"),
    ],
)
def test_the_runner_is_the_flag_then_the_environment_then_the_fallback(
    explicit, environ, fallback, expected
):
    """`VIBEY_OLLAMA_URL` is what the fallback workflows already export; before this,
    `sample_model` ignored it and always read 127.0.0.1."""
    resolved = OllamaModelSampler.resolve_base_url(explicit, environ=environ, fallback=fallback)
    assert resolved == expected
    sampler = OllamaModelSampler(explicit, environ=environ, fallback_url=fallback)
    assert sampler.base_url == expected


def test_sample_model_reads_the_runner_the_environment_names(monkeypatch):
    urls: list[str] = []
    monkeypatch.setenv(OLLAMA_URL_ENV, "http://env-runner:7/")
    monkeypatch.setattr(fit.shutil, "which", lambda _: "/usr/bin/curl")
    monkeypatch.setattr(fit, "_run", lambda *cmd: urls.append(cmd[-1]) or "")
    assert sample_model("m") is None
    assert urls == ["http://env-runner:7/api/ps", "http://env-runner:7/api/tags"]
    urls.clear()
    assert sample_model("m", "http://flag:8") is None
    assert urls[0] == "http://flag:8/api/ps"


def test_a_model_that_is_not_loaded_says_its_size_is_a_lower_bound():
    """Weights on disk understate what loading occupies; the verdict must say which
    reading it was built on rather than let one pass for the other."""
    cold = Model(name="qwen2.5-coder:14b", size_gb=8.99, context_length=32768, resident=False)
    comfortable = Machine(total_gb=64.0, free_gb=40.0, swap_used_gb=0.0, swap_total_gb=8.0)
    est = estimate_from([Observation(4096, 60.0, 1)])
    verdict = decide(comfortable, cold, est, queue_depth=0, payload_bytes=4096, deadline_s=900)
    assert verdict.verdict == ADMIT
    stated = (
        "qwen2.5-coder:14b is not loaded: 8.99 GB is its weights on disk, a lower bound on"
        " what loading it will occupy — the context's KV cache comes on top"
    )
    assert verdict.notes == (stated,)
    warm = decide(comfortable, MODEL, est, queue_depth=0, payload_bytes=4096, deadline_s=900)
    assert warm.notes == ()


# -- one context sizer for every local call (#135) -------------------------------------


@pytest.mark.parametrize(
    "chars", [0, 1, 6143, 6144, 6147, 60_000, 92_159, 92_160, 92_163, 10_000_000]
)
def test_the_default_sizer_is_exactly_the_rule_local_review_shipped_with(chars):
    """Moving the rule into one class must not move a single window: these are the
    values `local_review._num_ctx` returned, across both clamps and the line between."""
    expected = min(32768, max(4096, chars // 3 + 2048))
    assert ContextSizer().num_ctx(chars) == expected


def test_every_number_in_the_sizer_is_a_setting():
    sizer = ContextSizer(
        floor_tokens=1024, ceiling_tokens=8192, chars_per_token=4, reserve_tokens=512
    )
    assert sizer.num_ctx(0) == 1024
    assert sizer.num_ctx(4000) == 1512
    assert sizer.num_ctx(1_000_000) == 8192
    assert isinstance(sizer, ContextSizerInterface)


@pytest.mark.parametrize(
    "kw, message",
    [
        ({"chars_per_token": 0}, "chars_per_token"),
        ({"floor_tokens": 9000, "ceiling_tokens": 8192}, "floor_tokens"),
    ],
)
def test_a_sizer_that_could_not_size_anything_is_refused(kw, message):
    with pytest.raises(ValueError, match=message):
        ContextSizer(**kw)
