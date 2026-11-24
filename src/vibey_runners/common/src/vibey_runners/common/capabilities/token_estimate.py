# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one token estimate a loop's capability budgets are measured in (SP-LOOPS Phase 5, R8).

`[loops] capability_prompt_tokens` and `capability_answer_tokens` are written in tokens, but a
loop that lists its own capabilities only ever holds text. This turns one into the other, the
same way everywhere: characters over `CHARS_PER_TOKEN`, rounded up, so a budget can never be
overrun by rounding and empty text costs nothing. Declared by
`interfaces/token_estimate_interface.py::TokenEstimateInterface`.
"""

from __future__ import annotations

from typing import Final

from vibey_runners.common.capabilities.interfaces.token_estimate_interface import (
    TokenEstimateInterface,
)


class TokenEstimate:
    """Declared by `interfaces/token_estimate_interface.py::TokenEstimateInterface`."""

    CHARS_PER_TOKEN: Final = 4
    """Characters per estimated token. It is the local runner's own estimate (qwenloop's
    `application/runner.py`), and no tokenizer is available here: this package is stdlib only."""

    def tokens(self, text: str) -> int:
        return (len(text) + self.CHARS_PER_TOKEN - 1) // self.CHARS_PER_TOKEN  # ceil, in ints

    def chars(self, tokens: int) -> int:
        return tokens * self.CHARS_PER_TOKEN


TOKEN_ESTIMATE: Final[TokenEstimateInterface] = TokenEstimate()
"""The estimate every budget reader shares; the class holds no state."""
