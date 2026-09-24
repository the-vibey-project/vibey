# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Engine descriptors: data, not code paths (rotation-and-engines.md §2). A
fifth engine is a new descriptor plus an adapter, with no change to
domain/rotation.py.

The effort projections for claudeloop, codexloop, and cursorloop were
originally transcribed from rotation-and-engines.md §3, never independently
checked against a real `<binary> run --help`. agyloop's effort_projection
was verified against installed agyloop 0.1.0 on 2026-08-14 and confirmed
correct. The rest were verified for the first time on 2026-08-18 by adding
LoopProcessAdapter.help_text and running the conformance suite's `flags`
check for real against all four installed binaries -- claudeloop's own
effort_projection also checked out, but every isolation_flags entry across
claudeloop/codexloop/cursorloop turned out to be fabricated (agyloop's own
--safe flag is real and passed), and codexloop's entire effort_projection
was invalid: `--effort` does not exist on `codexloop run` at all (confirmed
against both --help and cli/commands/run.py directly -- the real flags are
--run-id/--transport/--model/--max-turns/--max-wait/--stream-ui only;
codexloop has no CLI-level way to set effort/reasoning depth at invocation
time, per domain/model_profile.py it starts at Effort.MEDIUM and can only
change via a runtime SetEffort event, not a flag). Every invocation at any
non-empty effort_projection entry would have failed outright at argument
parsing. Fixed to empty argv (the same behavior codexloop already has by
default) rather than guess at unverified flags -- codexloop/cursorloop
aren't authenticated in this environment, so a live end-to-end invocation
wasn't possible to confirm a replacement; empty argv is the only change
here guaranteed not to make things worse, since it removes a flag that
would otherwise be rejected outright.
"""

from vibey.domain.config import ClaudeloopLocalConfig
from vibey.domain.effort import Effort
from vibey.domain.engine import (
    Capability,
    EngineDescriptor,
    EngineId,
    EngineInvocation,
    EngineTier,
    IsolationLevel,
)

_CLAUDELOOP_ENV = ("CLAUDELOOP_*", "CLAUDE_CODE_*", "CLAUDE_CONFIG_DIR", "ANTHROPIC_*")

CLAUDELOOP = EngineDescriptor(
    engine_id=EngineId.CLAUDELOOP,
    binary="claudeloop",
    min_version="0.1.0",
    state_dir=".claudeloop",
    done_marker="CLAUDELOOP_TASK_FULLY_COMPLETE",
    auth_env=("ANTHROPIC_API_KEY",),
    # claudeloop's own settings, and Claude Code's: its config directory, its
    # CLAUDE_CODE_* switches and the ANTHROPIC_* endpoint, model and credential names.
    env_passthrough=_CLAUDELOOP_ENV,
    capabilities=frozenset(
        {
            Capability.SAVEPOINTS,
            Capability.UNWIND,
            Capability.STRUCTURED_VERDICT,
            Capability.MID_RUN_PROMPT,
            Capability.MID_RUN_MODEL,
            Capability.MID_RUN_EFFORT,
            Capability.SLASH_COMMANDS,
            Capability.SNAPSHOT,
            Capability.SANDBOX,
        }
    ),
    effort_projection={
        Effort.TRIVIAL: EngineInvocation(
            ("--preset", "low", "--effort", "low"), achieved=Effort.TRIVIAL
        ),
        Effort.LOW: EngineInvocation(
            ("--preset", "low", "--effort", "medium"), achieved=Effort.LOW
        ),
        Effort.STANDARD: EngineInvocation(
            ("--preset", "medium", "--effort", "high"), achieved=Effort.STANDARD
        ),
        Effort.HIGH: EngineInvocation(
            ("--preset", "high", "--effort", "high"), achieved=Effort.HIGH
        ),
        Effort.MAX: EngineInvocation(("--preset", "high", "--effort", "max"), achieved=Effort.MAX),
    },
    session_verb="sessions",
    # --permission-mode is real (confirmed via --help), but its actual value
    # vocabulary is Literal["bypass", "manual", "accept-edits", "plan",
    # "auto"] (domain/permission.py in the claudeloop repo) -- "container"
    # and "vm" were never valid values. claudeloop has no verified
    # container/VM isolation mechanism today; empty argv is honest about
    # that rather than passing a value the CLI would reject.
    isolation_flags={
        IsolationLevel.WORKTREE: (),
        IsolationLevel.CONTAINER: (),
        IsolationLevel.VM: (),
    },
    cost_per_mtok_in=3.0,
    cost_per_mtok_out=15.0,
    context_window=200_000,
    base_weight=3,
)

CODEXLOOP = EngineDescriptor(
    engine_id=EngineId.CODEXLOOP,
    binary="codexloop",
    min_version="0.1.0",
    state_dir=".codexloop",
    done_marker="CODEXLOOP_TASK_FULLY_COMPLETE",
    auth_env=("OPENAI_API_KEY",),
    # codexloop's settings and the Codex CLI's (CODEX_HOME, CODEX_API_KEY), the OpenAI
    # endpoint names, and the Azure OpenAI pair codexloop's Azure lane authenticates
    # with -- a model endpoint key, not a cloud-control credential.
    env_passthrough=(
        "CODEXLOOP_*",
        "CODEX_*",
        "OPENAI_*",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
    ),
    capabilities=frozenset(
        {
            Capability.SAVEPOINTS,
            Capability.UNWIND,
            Capability.STRUCTURED_VERDICT,
            Capability.SNAPSHOT,
            Capability.SANDBOX,
        }
    ),
    # codexloop's `run` has no --effort flag at all (confirmed via --help
    # and cli/commands/run.py directly) and no other CLI-level way to set
    # effort/reasoning depth at invocation. Per domain/model_profile.py it
    # always starts at its own internal Effort.MEDIUM and can only change
    # via a runtime SetEffort event mid-run, not a launch flag. Empty argv
    # for every level is the honest projection: vibey's effort request
    # doesn't change codexloop's behavior today, whereas the previous
    # ("--effort", ...) argv would have made every real invocation fail
    # outright at argument parsing.
    effort_projection={
        Effort.TRIVIAL: EngineInvocation((), achieved=Effort.STANDARD),
        Effort.LOW: EngineInvocation((), achieved=Effort.STANDARD),
        Effort.STANDARD: EngineInvocation((), achieved=Effort.STANDARD),
        Effort.HIGH: EngineInvocation((), achieved=Effort.STANDARD),
        Effort.MAX: EngineInvocation(
            (), achieved=Effort.STANDARD, notes="codexloop has no CLI-level effort control"
        ),
    },
    session_verb="threads",
    # Same reasoning as claudeloop's isolation_flags above: --sandbox and
    # --approval aren't real codexloop run flags (confirmed via --help),
    # and no verified container/VM mechanism exists for codexloop today.
    isolation_flags={
        IsolationLevel.WORKTREE: (),
        IsolationLevel.CONTAINER: (),
        IsolationLevel.VM: (),
    },
    cost_per_mtok_in=2.0,
    cost_per_mtok_out=8.0,
    context_window=200_000,
    base_weight=2,
    # `codexloop run` doesn't accept --cwd yet -- confirmed directly:
    # `codexloop run <plan> --cwd <dir>` fails at argument parsing with
    # "No such option: --cwd" before the process ever starts. build_argv()
    # appending it unconditionally meant LoopProcessAdapter could never
    # actually drive codexloop; caught by a real subprocess-level
    # conformance test (tests/live/test_scripted_binary_conformance.py),
    # not assumed. Safe without it: LoopProcessAdapter.start() already
    # spawns the subprocess with the OS-level cwd set to the worktree
    # (create_subprocess_exec(..., cwd=spec.worktree_path)), and codexloop's
    # own bootstrap.py falls back to Path.cwd() when --cwd is absent.
    supports_cwd_flag=False,
)

CURSORLOOP = EngineDescriptor(
    engine_id=EngineId.CURSORLOOP,
    binary="cursorloop",
    min_version="0.1.0",
    state_dir=".cursorloop",
    done_marker="CURSORLOOP_TASK_FULLY_COMPLETE",
    auth_env=("CURSOR_API_KEY",),
    env_passthrough=("CURSORLOOP_*", "CURSOR_*"),
    capabilities=frozenset(
        {
            Capability.SAVEPOINTS,
            Capability.UNWIND,
            Capability.SNAPSHOT,
            Capability.SANDBOX,
        }
    ),
    effort_projection={
        Effort.TRIVIAL: EngineInvocation(("--model", "composer-fast"), achieved=Effort.TRIVIAL),
        Effort.LOW: EngineInvocation(("--model", "composer"), achieved=Effort.LOW),
        Effort.STANDARD: EngineInvocation(("--model", "grok-4.5"), achieved=Effort.STANDARD),
        Effort.HIGH: EngineInvocation(("--model", "grok"), achieved=Effort.HIGH),
        Effort.MAX: EngineInvocation(("--model", "grok-xhigh"), achieved=Effort.MAX),
    },
    session_verb="agents",
    # cursorloop is the only engine whose `run` takes the plan as a flag
    # rather than a positional (`cursorloop run --plan <path>`); confirmed
    # against the installed 0.6.0 binary's --help. Passing it positionally
    # made every cursorloop run die at argument parsing -- no run dir, no
    # events, no snapshot -- which is exactly how conformance reported it.
    plan_flag="--plan",
    # --hooks-policy isn't a real cursorloop run flag (confirmed via
    # --help: the closest real flag, --managed-hooks/--no-managed-hooks, is
    # about merging autonomy hooks.json, not container/VM sandboxing). No
    # verified isolation mechanism exists for cursorloop today; same
    # reasoning as claudeloop/codexloop's isolation_flags above.
    isolation_flags={
        IsolationLevel.WORKTREE: (),
        IsolationLevel.CONTAINER: (),
        IsolationLevel.VM: (),
    },
    cost_per_mtok_in=2.5,
    cost_per_mtok_out=10.0,
    context_window=128_000,
    base_weight=2,
)

AGYLOOP = EngineDescriptor(
    engine_id=EngineId.AGYLOOP,
    binary="agyloop",
    min_version="0.1.0",
    state_dir=".agyloop",
    done_marker="AGYLOOP_TASK_FULLY_COMPLETE",
    auth_env=("GOOGLE_API_KEY",),
    # agyloop's and Antigravity's settings, and the Gemini developer-lane key. The
    # Vertex lane's cloud credentials (GOOGLE_ACCESS_TOKEN, CLOUDSDK_AUTH_ACCESS_TOKEN,
    # GOOGLE_APPLICATION_CREDENTIALS) are deliberately NOT here: a project that runs
    # agyloop on Vertex declares them under `engine_environment.engines.agyloop`.
    env_passthrough=(
        "AGYLOOP_*",
        "ANTIGRAVITY_*",
        "GEMINI_API_KEY",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_GENAI_USE_ENTERPRISE",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
    ),
    capabilities=frozenset(
        {
            Capability.UNWIND,
            Capability.STRUCTURED_VERDICT,
            Capability.WEB_SEARCH,
            Capability.SNAPSHOT,
        }
    ),
    effort_projection={
        Effort.TRIVIAL: EngineInvocation(
            ("--preset", "low", "--effort", "low"), achieved=Effort.TRIVIAL
        ),
        Effort.LOW: EngineInvocation(
            ("--preset", "low", "--effort", "medium"), achieved=Effort.LOW
        ),
        Effort.STANDARD: EngineInvocation(
            ("--preset", "medium", "--effort", "high"), achieved=Effort.STANDARD
        ),
        Effort.HIGH: EngineInvocation(
            ("--preset", "high", "--effort", "high"), achieved=Effort.HIGH
        ),
        Effort.MAX: EngineInvocation(("--preset", "high", "--effort", "max"), achieved=Effort.MAX),
    },
    session_verb="sessions",
    isolation_flags={
        IsolationLevel.WORKTREE: (),
        IsolationLevel.CONTAINER: ("--safe",),
        IsolationLevel.VM: ("--safe",),
    },
    cost_per_mtok_in=0.5,
    cost_per_mtok_out=2.0,
    context_window=1_000_000,
    base_weight=1,
)

OPENCODE = EngineDescriptor(
    engine_id=EngineId.OPENCODE,
    binary="opencodeloop",
    min_version="0.1.0",
    state_dir=".opencodeloop",
    done_marker="OPENCODELOOP_TASK_FULLY_COMPLETE",
    # OpenCode is a provider multiplexer: authentication belongs to the
    # installed OpenCode CLI and must not be guessed from a provider-specific
    # environment variable here. `opencodeloop doctor` checks the CLI contract.
    auth_env=(),
    # Its own settings only. A provider key the operator's OpenCode configuration reads
    # from the environment (ANTHROPIC_API_KEY, OPENROUTER_API_KEY, ...) is declared
    # under `engine_environment.engines.opencode`, never guessed here.
    env_passthrough=("OPENCODELOOP_*", "OPENCODE_*"),
    capabilities=frozenset({Capability.STRUCTURED_VERDICT, Capability.SNAPSHOT}),
    # The OpenCode CLI accepts provider-specific model settings rather than a
    # portable effort flag. Empty argv is therefore intentional; the achieved
    # level is the adapter's conservative STANDARD ceiling until a provider
    # exposes a verified effort control.
    effort_projection={
        Effort.TRIVIAL: EngineInvocation(
            (), achieved=Effort.STANDARD, notes="OpenCode has no portable effort flag"
        ),
        Effort.LOW: EngineInvocation(
            (), achieved=Effort.STANDARD, notes="OpenCode has no portable effort flag"
        ),
        Effort.STANDARD: EngineInvocation((), achieved=Effort.STANDARD),
        Effort.HIGH: EngineInvocation(
            (), achieved=Effort.STANDARD, notes="OpenCode has no portable effort flag"
        ),
        Effort.MAX: EngineInvocation(
            (), achieved=Effort.STANDARD, notes="OpenCode has no portable effort flag"
        ),
    },
    session_verb="sessions",
    resume_run_id_flag="--run-id",
    isolation_flags={
        IsolationLevel.WORKTREE: (),
        IsolationLevel.CONTAINER: (),
        IsolationLevel.VM: (),
    },
    # OpenCode itself does not publish a stable price table: the selected
    # provider may be local or remote. The wrapper preserves provider usage in
    # raw events; fixed descriptor pricing is deliberately zero until a
    # provider-specific meter is configured rather than inventing a price.
    cost_per_mtok_in=0.0,
    cost_per_mtok_out=0.0,
    context_window=32_768,
    base_weight=1,
    tier=EngineTier.LOCAL,
)

QWENLOOP = EngineDescriptor(
    engine_id=EngineId.QWENLOOP,
    binary="qwenloop",
    min_version="0.1.0",
    state_dir=".qwenloop",
    done_marker="QWENLOOP_TASK_FULLY_COMPLETE",
    auth_env=(),
    # QWENLOOP_BASE_URL and QWENLOOP_MODEL also arrive through the adapter's overlay,
    # derived from VIBEY_OLLAMA_URL -- which itself never reaches the session.
    env_passthrough=("QWENLOOP_*",),
    capabilities=frozenset(Capability),
    effort_projection={
        Effort.TRIVIAL: EngineInvocation(("--max-turns", "8"), achieved=Effort.TRIVIAL),
        Effort.LOW: EngineInvocation(("--max-turns", "16"), achieved=Effort.LOW),
        Effort.STANDARD: EngineInvocation(("--max-turns", "40"), achieved=Effort.STANDARD),
        Effort.HIGH: EngineInvocation(("--max-turns", "64"), achieved=Effort.HIGH),
        Effort.MAX: EngineInvocation(("--max-turns", "96"), achieved=Effort.MAX),
    },
    session_verb="sessions",
    isolation_flags={
        IsolationLevel.WORKTREE: (),
        IsolationLevel.CONTAINER: (),
        IsolationLevel.VM: (),
    },
    cost_per_mtok_in=0.0,
    cost_per_mtok_out=0.0,
    context_window=32_768,
    base_weight=1,
    tier=EngineTier.LOCAL,
)


class ClaudeloopLocalDescriptors:
    """The claudeloop-local descriptor for one configured backend profile (ADR-0038).

    Declared by `interfaces/descriptors_interface.py`. A class rather than a constant
    because two of its facts are the operator's, not the code's: the claudeloop
    profile it runs (which carries the local server's base_url and model tiers) and
    the context window that profile was sized for.

    - **Same binary, same run layout.** `claudeloop`, `.claudeloop` runs and the
      claudeloop done marker: the profile changes where Claude Code sends requests,
      not how claudeloop writes a run.
    - **Effort is a model tier, never `--effort`.** A local profile does not forward
      `--effort` (claudeloop's `pass_effort` is off there), so every level passes
      `--profile <name>` plus a `--preset` that picks the profile's `model_low`,
      `model_medium` or `model_high`. The honest ceiling is STANDARD: HIGH and MAX
      run the profile's top tier and say they achieved STANDARD, so fidelity scoring
      sees a local model for what it is rather than for what it was asked to be.
    - **No credential, no price.** `auth_env=()` and 0/0 per million tokens: the
      profile scrubs the paid key, and claudeloop records every local turn at $0.
    - **STRUCTURED_VERDICT only when claimed.** A local model has to prove it can
      make the tool call a verdict is (`structured_verdict` in the config, then
      conformance); claimed and unproven, conformance fails and the engine is
      ineligible rather than trusted to report its own completion.
    """

    # claudeloop's own vocabulary: `--preset low|medium|high` selects the model
    # tier, and a local profile maps each tier onto one of its own models.
    _PRESETS: dict[Effort, tuple[str, Effort]] = {
        Effort.TRIVIAL: ("low", Effort.TRIVIAL),
        Effort.LOW: ("low", Effort.LOW),
        Effort.STANDARD: ("medium", Effort.STANDARD),
        Effort.HIGH: ("high", Effort.STANDARD),
        Effort.MAX: ("high", Effort.STANDARD),
    }
    _CAPABILITIES = frozenset(
        {
            Capability.SAVEPOINTS,
            Capability.UNWIND,
            Capability.MID_RUN_PROMPT,
            Capability.MID_RUN_MODEL,
            Capability.SLASH_COMMANDS,
            Capability.SNAPSHOT,
            Capability.SANDBOX,
        }
    )

    def build(self, config: ClaudeloopLocalConfig | None = None) -> EngineDescriptor:
        settings = config if config is not None else ClaudeloopLocalConfig()
        profile = ("--profile", settings.profile)
        capabilities = set(self._CAPABILITIES)
        if settings.structured_verdict:
            capabilities.add(Capability.STRUCTURED_VERDICT)
        return EngineDescriptor(
            engine_id=EngineId.CLAUDELOOP_LOCAL,
            binary=CLAUDELOOP.binary,
            # The release that shipped claudeloop's `--profile`; the conformance
            # `flags` check is what actually refuses a binary without it.
            min_version="0.8.0",
            state_dir=CLAUDELOOP.state_dir,
            done_marker=CLAUDELOOP.done_marker,
            auth_env=(),
            # The same binary reads the same variables; the profile scrubs the paid key.
            env_passthrough=CLAUDELOOP.env_passthrough,
            capabilities=frozenset(capabilities),
            effort_projection={
                effort: EngineInvocation(
                    (*profile, "--preset", preset),
                    achieved=achieved,
                    notes=""
                    if achieved is effort
                    else "a local model's honest ceiling is STANDARD; runs the top tier",
                )
                for effort, (preset, achieved) in self._PRESETS.items()
            },
            session_verb=CLAUDELOOP.session_verb,
            isolation_flags=CLAUDELOOP.isolation_flags,
            cost_per_mtok_in=0.0,
            cost_per_mtok_out=0.0,
            context_window=settings.context_window,
            base_weight=1,
            tier=EngineTier.LOCAL,
            doctor_args=profile,
        )


CLAUDELOOP_LOCAL = ClaudeloopLocalDescriptors().build()

DEFAULT_DESCRIPTORS: tuple[EngineDescriptor, ...] = (
    CLAUDELOOP,
    CODEXLOOP,
    CURSORLOOP,
    AGYLOOP,
    OPENCODE,
)
# The local engines, each opt-in behind its own feature switch (ADR-0015, ADR-0038).
LOCAL_DESCRIPTORS: tuple[EngineDescriptor, ...] = (QWENLOOP, CLAUDELOOP_LOCAL)
ALL_DESCRIPTORS: tuple[EngineDescriptor, ...] = (*DEFAULT_DESCRIPTORS, *LOCAL_DESCRIPTORS)

BY_ENGINE_ID: dict[EngineId, EngineDescriptor] = {d.engine_id: d for d in ALL_DESCRIPTORS}
