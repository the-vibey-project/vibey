# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the project is about, in a sentence, for a research query.

The research stage is handed a bare topic (`prior-art`, `libraries`, `api-docs`), which is
useless as a search on its own. The intake in the ledger says what is being built: its
`## Objective` section's first sentence if it has one, else its first line of prose.
"""

import re
from collections.abc import Sequence

from vibey.application.design import DesignEvent
from vibey.domain.ledger import EventKind

_OBJECTIVE = re.compile(r"^#{1,3}\s*objective\s*$", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def research_context(events: Sequence[DesignEvent]) -> str:
    """The project's objective in one sentence, or '' when the ledger has no intake."""
    for event in events:
        if event.kind is not EventKind.TRANSCRIPT_RECORDED:
            continue
        text = str(event.payload.get("text", ""))
        return _first_sentence(_objective_paragraph(text))
    return ""


def _objective_paragraph(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if _OBJECTIVE.match(line.strip()):
            body = [ln.strip() for ln in lines[index + 1 :]]
            paragraph: list[str] = []
            for ln in body:
                if not ln and not paragraph:
                    continue
                if not ln or ln.startswith("#"):
                    break
                paragraph.append(ln)
            return " ".join(paragraph)
    prose = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    return prose[0] if prose else ""


def _first_sentence(paragraph: str) -> str:
    return _SENTENCE_END.split(paragraph, maxsplit=1)[0].strip()
