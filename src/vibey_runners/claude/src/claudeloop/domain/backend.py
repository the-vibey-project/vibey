# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Backend profiles — which Anthropic-compatible endpoint a run talks to, and
what that choice implies for models, cost accounting, and the environment
Claude Code is started with. Pure: no I/O, no clock, no environment reads.

The default profile is Anthropic itself and changes nothing. A profile with a
``base_url`` is *local* (Ollama, or any server speaking the Anthropic Messages
API): Claude Code is pointed at it, the paid ``ANTHROPIC_API_KEY`` is blanked so
it can never leave the machine, every model tier must be named explicitly (the
``claude-*`` defaults do not exist there), and cost is recorded as zero because
Claude Code prices an unknown model at the default model's rate — a guess that
would otherwise feed ``--max-budget-usd``, the 80% budget downgrade, and a
supervisor's spend brake with dollars nobody spent.

See docs/guides/local-backend.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from claudeloop.domain.errors import BackendProfileError
from claudeloop.domain.interfaces.backend_interface import BackendIdentityInterface

CostMode = Literal["reported", "zero"]
COST_MODES: tuple[CostMode, ...] = ("reported", "zero")

IdentityKind = Literal["anthropic", "gateway", "local"]

#: Name of the implicit profile used when none is selected.
DEFAULT_PROFILE_NAME = "anthropic"
#: Ollama ignores the token, but Claude Code refuses to start without one.
#: Not a credential: a public placeholder for a server that checks nothing. A real
#: secret goes in an environment variable named by ``auth_token_env``.
DEFAULT_LOCAL_AUTH_TOKEN = "ollama"  # nosec B105

#: sysexits.h EX_CONFIG. A run that ended because its backend, as configured,
#: cannot serve it — unreachable, model missing, model failed to load. Distinct
#: from 1 (failed) so a supervisor can route it to a human without parsing text.
EXIT_BACKEND_MISCONFIGURED = 78
BACKEND_MISCONFIGURED_PREFIX = "backend misconfigured"

#: Keys a profile owns outright. ``extra_env`` may not set them: they carry the
#: guarantee that a local profile never sends a paid Anthropic key anywhere.
PROFILE_OWNED_ENV_KEYS: frozenset[str] = frozenset(
    {"ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"}
)

_ENV_NAME = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")
_ANTHROPIC_MODEL_PREFIX = "claude-"
_MODEL_TIERS = ("model_low", "model_medium", "model_high")
_LOCAL_MODEL_FIELDS = (*_MODEL_TIERS, "small_fast_model", "subagent_model")


@dataclass(frozen=True, slots=True)
class BackendIdentity:
    """Where a run's transcript lives, recorded in run meta so a session is never
    resumed against a backend that did not produce it.

    ``anthropic`` — the default endpoint. ``gateway:<url>`` — the default profile
    with an ambient ``ANTHROPIC_BASE_URL`` the operator set themselves.
    ``local:<url>`` — a profile with ``base_url``.
    """

    kind: IdentityKind = "anthropic"
    url: str = ""

    def __str__(self) -> str:
        return self.kind if not self.url else f"{self.kind}:{self.url}"

    @property
    def is_local(self) -> bool:
        return self.kind == "local"

    @staticmethod
    def normalise_url(url: str) -> str:
        """Whitespace and trailing slashes are not part of an endpoint's identity."""
        return url.strip().rstrip("/")

    @classmethod
    def parse(cls, text: str) -> BackendIdentity:
        """Inverse of ``str()``. Raises BackendProfileError on anything else."""
        kind, separator, url = text.strip().partition(":")
        if kind == "anthropic" and not separator:
            return cls()
        if kind == "gateway" and url:
            return cls(kind="gateway", url=cls.normalise_url(url))
        if kind == "local" and url:
            return cls(kind="local", url=cls.normalise_url(url))
        raise BackendProfileError(f"unrecognised backend identity {text!r}")

    def check_model(self, model: str) -> None:
        """Refuse switching a live run on this backend to a model it cannot serve —
        a ``claude-*`` id on a local backend would end the run on its next turn."""
        if self.is_local and model.strip().lower().startswith(_ANTHROPIC_MODEL_PREFIX):
            raise BackendProfileError(
                f"this run talks to {self}, which does not serve the Anthropic model "
                f"{model.strip()!r}; use low|medium|high or a model that backend has"
            )

    def check_server_tools(self) -> None:
        """Refuse enabling web search / deep research on a live local run."""
        if self.is_local:
            raise BackendProfileError(
                f"this run talks to {self}; web search and deep research need "
                "Anthropic's server-side tools, which a local backend cannot serve"
            )

    def resume_refusal(self, previous: BackendIdentityInterface | None) -> str | None:
        """Why this backend must not resume a session last run on ``previous``, or
        None when it may. Unknown history (``None``) never refuses: runs recorded
        before backends were tracked carry no identity."""
        if previous is None or (previous.kind, previous.url) == (self.kind, self.url):
            return None
        return (
            f"this session was last run against {previous}, but this run would use "
            f"{self}. A transcript does not move between backends: select the profile "
            "it was started with (--profile / CLAUDELOOP_PROFILE), or start a fresh "
            "`claudeloop run`."
        )


@dataclass(frozen=True, slots=True)
class BackendRuntime:
    """What the agent gateway and capacity probe need from a profile, already
    resolved: the environment overlay (applied on top of the inherited process
    environment, so it wins), the CLI to launch, and the accounting rules."""

    env: tuple[tuple[str, str], ...] = ()
    cli_path: str | None = None
    pass_effort: bool = True
    cost_mode: CostMode = "reported"
    local: bool = False
    # Whether the legacy done-marker substring may complete a run when no
    # structured verdict arrived (domain/completion.py).
    done_marker_fallback: bool = True

    def environment(self) -> dict[str, str]:
        return dict(self.env)


@dataclass(frozen=True, slots=True)
class BackendProfile:
    """One ``[profiles.<name>]`` table. Validated on construction, so an invalid
    profile can never reach the gateway. ``None`` on the tri-state fields means
    "derive from whether the profile is local"."""

    name: str = DEFAULT_PROFILE_NAME
    base_url: str = ""
    auth_token: str = DEFAULT_LOCAL_AUTH_TOKEN
    auth_token_env: str = ""
    model_low: str = ""
    model_medium: str = ""
    model_high: str = ""
    small_fast_model: str = ""
    subagent_model: str = ""
    context_window: int = 0
    max_output_tokens: int = 0
    cost_mode: CostMode | None = None
    pass_effort: bool | None = None
    disable_nonessential_traffic: bool | None = None
    done_marker_fallback: bool | None = None
    cli_path: str = ""
    extra_env: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise BackendProfileError("a backend profile needs a non-empty name")
        base = self.base_url.strip()
        if base and not base.startswith(("http://", "https://")):
            raise BackendProfileError(
                f"[profiles.{self.name}] base_url must be an http:// or https:// URL, "
                f"got {self.base_url!r}"
            )
        for label, value in (
            ("context_window", self.context_window),
            ("max_output_tokens", self.max_output_tokens),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BackendProfileError(
                    f"[profiles.{self.name}] {label} must be a non-negative integer "
                    f"(0 leaves Claude Code's own default), got {value!r}"
                )
        if self.cost_mode is not None and self.cost_mode not in COST_MODES:
            raise BackendProfileError(
                f"[profiles.{self.name}] cost_mode must be one of {COST_MODES}, "
                f"got {self.cost_mode!r}"
            )
        if self.auth_token_env and not _ENV_NAME.match(self.auth_token_env):
            raise BackendProfileError(
                f"[profiles.{self.name}] auth_token_env must name an environment "
                f"variable, got {self.auth_token_env!r}"
            )
        for key, _value in self.extra_env:
            if not _ENV_NAME.match(key):
                raise BackendProfileError(
                    f"[profiles.{self.name}] extra_env key {key!r} is not an "
                    "environment variable name"
                )
            if key in PROFILE_OWNED_ENV_KEYS:
                raise BackendProfileError(
                    f"[profiles.{self.name}] extra_env may not set {key}; use base_url, "
                    "auth_token or auth_token_env, which keep a paid key off a local "
                    "backend"
                )
        if self.is_local:
            self._validate_local()
        else:
            self._validate_anthropic()

    def _validate_local(self) -> None:
        missing = [tier for tier in _MODEL_TIERS if not str(getattr(self, tier)).strip()]
        if missing:
            raise BackendProfileError(
                f"[profiles.{self.name}] talks to {self.base_url} and must name every "
                f"model tier; missing {', '.join(missing)}. The claude-* defaults do not "
                "exist on a local backend."
            )
        for label in _LOCAL_MODEL_FIELDS:
            self._refuse_anthropic_id(label, str(getattr(self, label)))

    def _validate_anthropic(self) -> None:
        if self.auth_token_env:
            raise BackendProfileError(
                f"[profiles.{self.name}] auth_token_env only applies to a profile with "
                "base_url; the Anthropic backend authenticates through Claude Code"
            )
        if self.cost_mode == "zero":
            raise BackendProfileError(
                f'[profiles.{self.name}] cost_mode = "zero" would hide real Anthropic '
                "spend from every budget; only a profile with base_url may use it"
            )

    def _refuse_anthropic_id(self, label: str, model: str) -> None:
        if model.strip().lower().startswith(_ANTHROPIC_MODEL_PREFIX):
            raise BackendProfileError(
                f"profile {self.name!r} talks to {self.base_url}, which does not serve "
                f"the Anthropic model {model.strip()!r} ({label}); name a model that "
                "backend actually has"
            )

    @property
    def is_local(self) -> bool:
        return bool(self.base_url.strip())

    @property
    def effective_cost_mode(self) -> CostMode:
        if self.cost_mode is not None:
            return self.cost_mode
        return "zero" if self.is_local else "reported"

    @property
    def effective_pass_effort(self) -> bool:
        return (not self.is_local) if self.pass_effort is None else self.pass_effort

    @property
    def effective_disable_nonessential_traffic(self) -> bool:
        if self.disable_nonessential_traffic is None:
            return self.is_local
        return self.disable_nonessential_traffic

    @property
    def effective_done_marker_fallback(self) -> bool:
        """Off on a local backend: only a structured verdict — itself a tool call —
        may complete the run, so a model that cannot call tools cannot claim Done."""
        if self.done_marker_fallback is None:
            return not self.is_local
        return self.done_marker_fallback

    @property
    def effective_small_fast_model(self) -> str:
        """Claude Code's background model. On a local backend it defaults to the
        ``low`` tier, because Claude Code's own default is a claude-haiku id the
        backend does not have."""
        if self.small_fast_model.strip():
            return self.small_fast_model.strip()
        return self.model_low.strip() if self.is_local else ""

    def tier_models(self, *, low: str, medium: str, high: str) -> tuple[str, str, str]:
        """The low/medium/high model ids this profile resolves to, falling back to
        the given top-level ids for any tier the profile leaves blank."""
        return (
            self.model_low.strip() or low,
            self.model_medium.strip() or medium,
            self.model_high.strip() or high,
        )

    def required_models(self) -> tuple[str, ...]:
        """Every model id this profile will ask its backend for, deduplicated in
        tier order — what `doctor` checks is actually present."""
        ordered: list[str] = []
        for candidate in (
            self.model_low,
            self.model_medium,
            self.model_high,
            self.effective_small_fast_model,
            self.subagent_model,
        ):
            model = candidate.strip()
            if model and model not in ordered:
                ordered.append(model)
        return tuple(ordered)

    def check_model(self, model: str) -> None:
        """Refuse a resolved run model (e.g. a raw ``--model`` id) the backend
        cannot serve."""
        if self.is_local:
            self._refuse_anthropic_id("model", model)

    def check_tools(self, *, web_search: bool, deep_research: bool) -> None:
        """Web search and deep research are Anthropic server-side tools; a local
        backend cannot execute them, so asking for them is refused up front rather
        than failing somewhere inside a turn."""
        if not self.is_local:
            return
        wanted = [
            flag
            for flag, enabled in (("web_search", web_search), ("deep_research", deep_research))
            if enabled
        ]
        if wanted:
            raise BackendProfileError(
                f"{' and '.join(wanted)} need Anthropic's server-side tools; profile "
                f"{self.name!r} talks to {self.base_url}, which cannot serve them"
            )

    def identity(self, *, ambient_base_url: str = "") -> BackendIdentity:
        if self.is_local:
            return BackendIdentity(kind="local", url=BackendIdentity.normalise_url(self.base_url))
        ambient = BackendIdentity.normalise_url(ambient_base_url)
        if ambient:
            return BackendIdentity(kind="gateway", url=ambient)
        return BackendIdentity()

    def env_overlay(self, *, auth_token: str) -> dict[str, str]:
        """The environment Claude Code is started with on top of the inherited one.

        The Anthropic profile adds nothing unless a key asks for it. A local profile
        points Claude Code at ``base_url``, blanks ``ANTHROPIC_API_KEY`` (an empty
        value overrides an inherited paid key; the SDK merges this dict last), and
        maps Claude Code's haiku/sonnet/opus aliases onto the profile's tiers so no
        ``claude-*`` id is ever sent to the backend. ``extra_env`` is applied last.
        """
        env: dict[str, str] = {}
        if self.is_local:
            env["ANTHROPIC_BASE_URL"] = self.base_url.strip()
            env["ANTHROPIC_AUTH_TOKEN"] = auth_token
            env["ANTHROPIC_API_KEY"] = ""
            env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = self.model_low.strip()
            env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = self.model_medium.strip()
        small_fast = self.effective_small_fast_model
        if small_fast:
            env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = small_fast
            env["ANTHROPIC_SMALL_FAST_MODEL"] = small_fast
        if self.subagent_model.strip():
            env["CLAUDE_CODE_SUBAGENT_MODEL"] = self.subagent_model.strip()
        if self.context_window > 0:
            env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] = str(self.context_window)
            env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = str(self.context_window)
        if self.max_output_tokens > 0:
            env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(self.max_output_tokens)
        if self.effective_disable_nonessential_traffic:
            env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        env.update(dict(self.extra_env))
        return env

    def runtime(self, *, auth_token: str) -> BackendRuntime:
        return BackendRuntime(
            env=tuple(self.env_overlay(auth_token=auth_token).items()),
            cli_path=self.cli_path.strip() or None,
            pass_effort=self.effective_pass_effort,
            cost_mode=self.effective_cost_mode,
            local=self.is_local,
            done_marker_fallback=self.effective_done_marker_fallback,
        )
