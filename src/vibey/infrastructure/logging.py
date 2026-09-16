# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""structlog configuration with separate transports.

Three sinks, so one operator's need does not crowd out another's:

1. **Human console** -- stderr, ``ConsoleRenderer``, for someone watching.
2. **JSON console** -- stderr, one object per line (``transport=console_json``),
   for whatever is capturing the process.
3. **Optional file** -- ``--log-file``, JSON lines, *in addition to* the
   console rather than instead of it.

Every payload passes through ``ledger.redact``, the same redactor the event
ledger uses: a secret must not be safe in one sink and leaked in another.

The per-project event ledger is a different thing entirely -- it is durable
domain history, not diagnostics. This module never writes to it.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import structlog
from structlog.stdlib import BoundLogger, LoggerFactory, ProcessorFormatter

from vibey.domain.interfaces.correlation_interface import CorrelationIdInterface
from vibey.domain.verbosity import LogPlan
from vibey.infrastructure.interfaces.logging_interface import CorrelationLogContextInterface
from vibey.infrastructure.ledger.redact import redact_payload

# Chatty libraries that are noise unless the operator explicitly widened the
# net with -vv. asyncpg in particular logs every statement at DEBUG.
_THIRD_PARTY_LOGGERS = ("asyncpg", "asyncio", "httpx", "httpcore", "urllib3", "textual")

# What the delivery correlation id is rendered under by default -- the same
# name the ledger column carries, so a log line and an `event` row join on a
# field spelled identically in both places. A key rather than a literal at the
# binding site, so a deployment whose collector already reserves this name can
# bind under another (ADR-0018).
CORRELATION_LOG_FIELD = "correlation_id"


def _redact_processor(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    return redact_payload(dict(event_dict))


def _tagged_json(transport: str) -> Any:
    def render(logger: Any, method_name: str, event_dict: MutableMapping[str, Any]) -> str:
        payload = dict(event_dict)
        payload.setdefault("transport", transport)
        return str(structlog.processors.JSONRenderer()(logger, method_name, payload))

    return render


def configure_logging(
    plan: LogPlan,
    *,
    log_file: Path | None = None,
    human_console: bool = True,
) -> None:
    """Install the console handlers and, optionally, a file handler.

    ``human_console=False`` when the Textual dashboard owns the TTY -- a
    ConsoleRenderer writing to stderr underneath a full-screen app corrupts
    the display.
    """
    level_value = getattr(logging, plan.level, logging.INFO)

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_processor,
    ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared,
            ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level_value),
        cache_logger_on_first_use=False,
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level_value)

    if human_console:
        human = logging.StreamHandler(sys.stderr)
        human.setLevel(level_value)
        human.setFormatter(
            ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(),
                foreign_pre_chain=shared,
            )
        )
        root.addHandler(human)

    json_console = logging.StreamHandler(sys.stderr)
    json_console.setLevel(level_value)
    json_console.setFormatter(
        ProcessorFormatter(
            processor=_tagged_json("console_json"),
            foreign_pre_chain=shared,
        )
    )
    root.addHandler(json_console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level_value)
        file_handler.setFormatter(
            ProcessorFormatter(
                processor=_tagged_json("file"),
                foreign_pre_chain=shared,
            )
        )
        root.addHandler(file_handler)

    apply_third_party_level(plan)


def apply_third_party_level(plan: LogPlan) -> None:
    """Raise third-party loggers' floor unless -vv asked for them.

    Raising the floor rather than removing their handlers keeps a genuine
    library error visible at any verbosity.
    """
    level_value = getattr(logging, plan.level, logging.INFO)
    target = level_value if plan.include_third_party else max(level_value, logging.WARNING)
    for name in _THIRD_PARTY_LOGGERS:
        logging.getLogger(name).setLevel(target)


def get_logger(**initial_context: Any) -> BoundLogger:
    logger: BoundLogger = structlog.get_logger(**initial_context)
    return logger


class CorrelationLogContext:
    """Puts one delivery's correlation id on every log line inside its scope.

    Ambient rather than threaded through call sites: a delivery crosses six
    phases, several handlers and any number of repositories, and a parameter
    every one of them has to remember to pass is a parameter one of them will
    not. ``merge_contextvars`` is already the first processor in the shared
    chain, so a binding here reaches all three sinks -- human console, JSON
    console and the optional file -- and survives an ``await``.

    structlog's context vars, not ``vibey_bootstrap``'s ``correlation_scope``
    (ADR-0017): that package is deliberately not a dependency of ``vibey`` --
    it carries the Azure SDK and OpenTelemetry -- and its ``CorrelationFilter``
    attaches to stdlib ``LogRecord`` attributes, which this module's
    ``ProcessorFormatter`` pipeline does not render. Reaching for it here would
    add a dependency graph to gain nothing.

    **Nothing in production enters this scope yet, and that is disclosed rather
    than implied.** Issue #89 has two halves: every event of a delivery carrying
    one id, and every log line carrying it too. The first is live at every write
    site; this is the second, and it is built, conformance-checked and tested
    but not yet entered -- so today's log lines still carry no
    ``correlation_id``. The scope belongs at the job execution boundary in
    ``WorkerLoop``, which cannot reach this class directly: ``application/`` may
    not import ``infrastructure/``, so wiring it needs an application-side port
    and a binding in the composition root, and that is its own change rather
    than a line added here. Recording the gap keeps two readings apart -- "this
    delivery emitted no correlated lines" and "nothing emits correlated lines
    yet" are different facts, and only the second is true.
    """

    def __init__(self, field: str = CORRELATION_LOG_FIELD) -> None:
        self._field = field

    @property
    def field(self) -> str:
        """The key the id is rendered under."""
        return self._field

    def bind(self, correlation_id: CorrelationIdInterface) -> None:
        structlog.contextvars.bind_contextvars(**{self._field: str(correlation_id.value)})

    def clear(self) -> None:
        structlog.contextvars.unbind_contextvars(self._field)

    @contextmanager
    def bound(self, correlation_id: CorrelationIdInterface) -> Iterator[str]:
        """Bind for the duration of the block, restoring whatever was bound
        before it however the block ends.

        ``structlog.contextvars.bound_contextvars`` rather than
        ``bind`` + ``finally: clear``: clearing *unbinds*, so leaving an inner
        scope would erase an outer delivery's binding instead of putting it
        back, and every later line in the outer scope would silently lose the
        id -- exactly the property this class exists to guarantee. structlog
        already saves and restores the prior token; reimplementing it produced
        a strictly worse primitive (ADR-0017: if the dependency already does
        it, use it).
        """
        value = str(correlation_id.value)
        with structlog.contextvars.bound_contextvars(**{self._field: value}):
            yield value


# `mypy --strict` checks this assignment, and that is its whole purpose: a
# `runtime_checkable` Protocol only hasattr-checks member *names* at runtime,
# so an `isinstance` test keeps passing after a signature has drifted. The
# annotation is the conformance check with teeth.
_CONFORMS: CorrelationLogContextInterface = CorrelationLogContext()


class StructlogAppLogger:
    """Adapter satisfying application.interfaces.Logger."""

    def __init__(self, bound: BoundLogger | None = None, **context: Any) -> None:
        self._log: BoundLogger = bound if bound is not None else get_logger(**context)

    def bind(self, **kwargs: Any) -> StructlogAppLogger:
        return StructlogAppLogger(self._log.bind(**kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log.debug(event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log.info(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log.warning(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log.error(event, **kwargs)


class NullAppLogger:
    """The default, so nothing is obliged to configure logging to run."""

    def bind(self, **kwargs: Any) -> NullAppLogger:
        del kwargs
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        del event, kwargs

    def info(self, event: str, **kwargs: Any) -> None:
        del event, kwargs

    def warning(self, event: str, **kwargs: Any) -> None:
        del event, kwargs

    def error(self, event: str, **kwargs: Any) -> None:
        del event, kwargs
