# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Who a person-made record says made it: a label the caller chose, or its account.

Two commands record who acted, and both the same way: `vibey budget set --by` and
`vibey answer --by`. The label is the name the caller gave (the VS Code extension says
`vibey-vscode`), or the operating system's account when it gave none; the account is
always recorded beside it, so the record says who ran the command whatever the label.
A label is a name for the record, never an authority: nothing admits or refuses on it.

It is printed and stored as given, so it must be one line of visible text: not empty,
not over `MAX_LENGTH`, and free of control and formatting characters, which could forge
a line of output or reorder one. Each command refuses a bad label with its own error,
so the refusal reads in that command's words.
"""

import unicodedata
from typing import ClassVar, Final

from vibey.domain.errors import InvalidActorLabel, VibeyError


class ActorLabelPolicy:
    """Checks a label a caller named itself by, or falls back to the account. Pure.

    Declared by `interfaces/actor_label_interface.py::ActorLabelPolicyInterface`."""

    MAX_LENGTH: ClassVar[int] = 200
    """Long enough for any account or tool name; short enough for one line of output."""

    def __init__(
        self,
        *,
        subject: str = "the name a record is made under",
        error: type[VibeyError] = InvalidActorLabel,
    ) -> None:
        self._subject = subject
        self._error = error

    def resolve(self, label: str | None, *, account: str) -> str:
        if label is None:
            return account
        name = label.strip()
        if not name:
            raise self._error(f"{self._subject} cannot be empty")
        if len(name) > self.MAX_LENGTH:
            raise self._error(f"{self._subject} is over {self.MAX_LENGTH} characters")
        if any(unicodedata.category(char).startswith("C") for char in name):
            raise self._error(f"{self._subject} cannot contain control or formatting characters")
        return name


ACTOR_LABELS: Final = ActorLabelPolicy()
"""The policy with vibey's general wording. Stateless, so one instance serves."""
