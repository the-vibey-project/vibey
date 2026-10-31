# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`CLAUDE.md`, `AGENTS.md` and `GEMINI.md` are generated from one source (#1688).

    python scripts/agent_instructions.py render   # rewrite the three files
    python scripts/agent_instructions.py check    # exit 1 if one differs from what the source makes

The three files had diverged: AGENTS.md carried a non-negotiable the others lacked, cited a
different Article for the same rule, and each repeated facts (the ADR count, the CI matrix) that
drift when edited in three places. `docs/agents/instructions.toml` (declared in
`scripts/agent_instructions.toml`) is now the one source, with a `full` and a `brief` edition of
every block and each difference between doors declared, with its reason, beside the text. `check`
is the check that says out loud when a door was edited by hand or not regenerated
(sub-doctrine 12.e).

The block between `<!-- vibey:begin -->` and `<!-- vibey:end -->` is the provisioner's
(`src/vibey/domain/provision.py`): it is carried over from the file on disk, never written here.
"""

from __future__ import annotations

import argparse
import difflib
import sys
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.agent_instructions_interface import AgentInstructionsInterface
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.agent_instructions_interface import (  # type: ignore[import-not-found,no-redef]
        AgentInstructionsInterface,
    )

SCRIPT = "scripts/agent_instructions.py"
DEFAULT_CONFIG = "scripts/agent_instructions.toml"
REPO = Path(__file__).resolve().parents[1]

BEGIN_MARKER = "<!-- vibey:begin -->"
END_MARKER = "<!-- vibey:end -->"
EDITIONS = ("full", "brief")


class AgentInstructions(AgentInstructionsInterface):
    """Implements `AgentInstructionsInterface` over a source table and a repository root."""

    def __init__(self, source: Mapping[str, Any], root: Path, source_name: str) -> None:
        self._source = source
        self._root = root
        self._name = source_name

    @classmethod
    def load(cls, config: Path = REPO / DEFAULT_CONFIG, root: Path = REPO) -> AgentInstructions:
        declared = tomllib.loads(config.read_text(encoding="utf-8"))["agent_instructions"]
        name = str(declared["source"])
        source = tomllib.loads((root / name).read_text(encoding="utf-8"))
        return cls(source, root, name)

    # ------------------------------------------------------------------------------ the source

    def agents(self) -> list[str]:
        return list(self._source.get("agents", {}))

    def _agent(self, agent: str) -> Mapping[str, Any]:
        found: Mapping[str, Any] = self._source["agents"][agent]
        return found

    def problems(self) -> list[str]:
        found: list[str] = []
        known = set(self.agents())
        for agent in self.agents():
            table = self._agent(agent)
            if table.get("edition") not in EDITIONS:
                found.append(f"agents.{agent}.edition must be one of {', '.join(EDITIONS)}")
            if not table.get("file") or not table.get("title"):
                found.append(f"agents.{agent} needs a file and a title")
        seen: set[str] = set()
        for section in self._source.get("section", []):
            sid = str(section.get("id", ""))
            if not sid or sid in seen:
                found.append(f"section id {sid!r} is empty or used twice")
            seen.add(sid)
            if not section.get("heading"):
                found.append(f"section {sid} has no heading")
            if not section.get("item") and not str(section.get("full", "")).strip():
                found.append(f"section {sid} has neither a body nor items")
            item_ids: set[str] = set()
            for item in section.get("item", []):
                iid = str(item.get("id", ""))
                if not iid or iid in item_ids:
                    found.append(f"item id {iid!r} in section {sid} is empty or used twice")
                item_ids.add(iid)
                if not str(item.get("full", "")).strip():
                    found.append(f"item {iid} in section {sid} has no full text")
                if item.get("brief") == "" and not item.get("note"):
                    found.append(f"item {iid} is left out of the brief edition without a note")
                found.extend(self._unknown(known, item, f"item {iid}"))
        found.extend(self._unknown(known, self._source.get("appendix", {}), "the appendix"))
        return found

    @staticmethod
    def _unknown(known: set[str], block: Mapping[str, Any], label: str) -> list[str]:
        return [
            f"{label} names an unknown agent {agent!r}"
            for agent in block.get("agents", [])
            if agent not in known
        ]

    # --------------------------------------------------------------------------- the rendering

    def render(self, agent: str) -> str:
        table = self._agent(agent)
        edition = str(table["edition"])
        parts = [
            f"# {table['title']}",
            str(self._source["render"]["banner"]),
            self._pick(self._source["intro"], edition),
        ]
        for section in self._source.get("section", []):
            parts.append(self._section(section, agent, edition))
        block = self._carried_block(self._root / str(table["file"]))
        if block:
            parts.append(block)
        appendix = self._source.get("appendix", {})
        if agent in appendix.get("agents", []):
            parts.append(str(appendix["full"]))
        return "\n\n".join(part for part in parts if part) + "\n"

    @staticmethod
    def _pick(block: Mapping[str, Any], edition: str) -> str:
        """The `edition` text of a block; a `brief` it does not declare is the `full` text."""
        text = block.get(edition) if edition in block else block.get("full")
        return str(text or "")

    def _section(self, section: Mapping[str, Any], agent: str, edition: str) -> str:
        heading = section["heading"]
        if edition == "brief" and section.get("heading_brief"):
            heading = section["heading_brief"]
        chunk = [f"## {heading}"]
        body = self._pick(section, edition) if "full" in section else ""
        if body:
            chunk.append(body)
        items = [
            self._pick(item, edition)
            for item in section.get("item", [])
            if not item.get("agents") or agent in item["agents"]
        ]
        listed = "\n".join(text for text in items if text)
        if listed:
            chunk.append(listed)
        return "\n\n".join(chunk)

    @staticmethod
    def _carried_block(path: Path) -> str:
        """The provisioner's marker block as it is on disk, or nothing if the file has none."""
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8")
        begin, end = text.find(BEGIN_MARKER), text.find(END_MARKER)
        if begin < 0 or end < begin:
            return ""
        return text[begin : end + len(END_MARKER)]

    # ------------------------------------------------------------------------------- the check

    def differing(self) -> list[str]:
        found: list[str] = []
        for agent in self.agents():
            name = str(self._agent(agent)["file"])
            path = self._root / name
            wanted = self.render(agent)
            have = path.read_text(encoding="utf-8") if path.is_file() else ""
            if have == wanted:
                continue
            delta = list(
                difflib.unified_diff(
                    have.splitlines(), wanted.splitlines(), name, f"{name} (generated)", n=0
                )
            )
            first = next((line for line in delta[2:] if line[:1] in "+-"), "")
            found.append(
                f"{name} is not what {self._name} makes of it (first difference: {first[:100]})"
            )
        return found

    def write(self) -> list[str]:
        written: list[str] = []
        for agent in self.agents():
            name = str(self._agent(agent)["file"])
            text = self.render(agent)
            path = self._root / name
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")
                written.append(name)
        return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=SCRIPT, description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("render", "check"))
    parser.add_argument("--root", type=Path, default=REPO, help="the repository to render into")
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)
    instructions = AgentInstructions.load(args.config or args.root / DEFAULT_CONFIG, args.root)
    problems = instructions.problems()
    if problems:
        for problem in problems:
            print(f"{SCRIPT}: {problem}", file=sys.stderr)
        return 1
    if args.action == "render":
        written = instructions.write()
        print("rewrote: " + ", ".join(written) if written else "up to date")
        return 0
    differing = instructions.differing()
    for line in differing:
        print(f"{SCRIPT}: {line}", file=sys.stderr)
    if differing:
        print(f"{SCRIPT}: run `python {SCRIPT} render` and commit the result", file=sys.stderr)
    return 1 if differing else 0


if __name__ == "__main__":
    raise SystemExit(main())
