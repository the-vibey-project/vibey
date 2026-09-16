# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The default sink behind `interfaces.observability.Logger`.

The family implementation of that seam is `infrastructure.logging`'s
``StructlogAppLogger``, and a composition root should inject it. This module
is not a second one: `application/` may not import `infrastructure/`, so an
application object that is handed no logger has nothing to speak through --
and a worker that says nothing is exactly the failure this default exists to
prevent. It writes to the stdlib `logging` hierarchy that ``configure_logging``
already owns, so the line lands in every sink the operator configured
(human console, JSON console, and the optional ``--log-file``).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any


class StandardLibraryLogger:
    """A `Logger` backed by a stdlib logger of the caller's choosing.

    Bound context and per-call fields are rendered as ``key=value`` pairs
    after the event name rather than passed as ``extra=``: structlog's
    foreign-record chain drops `extra` attributes, and a field that survives
    in one sink but not another is worse than one rendered plainly in all of
    them. An injected ``StructlogAppLogger`` keeps them as real JSON fields.
    """

    def __init__(self, name: str, **context: Any) -> None:
        self._name = name
        self._log = logging.getLogger(name)
        self._context: dict[str, Any] = dict(context)

    def bind(self, **kwargs: Any) -> StandardLibraryLogger:
        return StandardLibraryLogger(self._name, **{**self._context, **kwargs})

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log.debug(self._render(event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self._log.info(self._render(event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log.warning(self._render(event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._log.error(self._render(event, kwargs))

    def _render(self, event: str, fields: Mapping[str, Any]) -> str:
        merged = {**self._context, **fields}
        return " ".join([event, *(f"{key}={value}" for key, value in merged.items())])
