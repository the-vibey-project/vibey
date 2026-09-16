# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The fit calculus (#263): both sides measured, the projection stated, the floor loud."""

from __future__ import annotations

import pytest

from vibey_gh import fit
from vibey_gh.cli import main
from vibey_gh.fit import (
    ADMIT,
    DEFER,
    FLOOR,
    DarwinMemorySampler,
    Estimate,
    LinuxMemorySampler,
    Machine,
    Model,
    Observation,
    TextFileReader,
    decide,
    estimate_from,
    headroom_gb,
    machine_sampler,
    sample_machine,
    sample_model,
    saturating_wait,
)

MACHINE = Machine(total_gb=25.77, free_gb=2.97, swap_used_gb=6.5, swap_total_gb=7.0)
MODEL = Model(name="qwen2.5-coder:14b", size_gb=10.52, context_length=9390)


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
