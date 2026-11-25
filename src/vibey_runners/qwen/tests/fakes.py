# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory fakes for qwenloop's declared seams, shared by the tests (no outside service)."""

import asyncio
import json
import os
import shutil
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from vibey_runners.common.capabilities.bundle import (
    DEFAULT_CAPABILITY_ANSWER_TOKENS,
    DEFAULT_CAPABILITY_PROMPT_TOKENS,
    DEFAULT_INSTRUCTION_FILES,
    DEFAULT_INSTRUCTION_MAX_BYTES,
)
from vibey_runners.common.capabilities.command_entry import CommandEntry
from vibey_runners.common.capabilities.interfaces.plugin_command_index_interface import (
    PluginCommandIndexInterface,
)
from vibey_runners.common.capabilities.interfaces.skill_index_interface import (
    SkillIndexInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_store_interface import (
    SnapshotDocumentStoreInterface,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
from vibey_runners.common.capabilities.skill_entry import SkillEntry
from vibey_runners.common.capabilities.skill_index import SkillIndex
from vibey_runners.common.capabilities.snapshot_document import DOCUMENT_VERSION, SnapshotDocument
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore
from vibey_runners.common.mcp.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface

from qwenloop.application.interfaces import OllamaProbeInterface

MEMORY_DIGEST = "sha256:" + "5e" * 32


class FakeOllamaModelProbe:
    """What an Ollama would say a model can do: as told, counting asks."""

    def __init__(self, reported: frozenset[str] | None = None) -> None:
        self.reported = reported
        self.asked: list[tuple[str, str]] = []

    def capabilities(self, base_url: str, model: str) -> frozenset[str] | None:
        self.asked.append((base_url, model))
        return self.reported


class FakeOllamaProbe:
    """An in-memory stand-in for the local-Ollama probe: answers as told, counts asks."""

    def __init__(self, available: bool = False) -> None:
        self.answer = available
        self.asked = 0

    def available(self) -> bool:
        self.asked += 1
        return self.answer


class MemoryMcpServer:
    """An MCP server held in memory behind the transport seam: it answers what the client writes
    from inside the writer, so no socket, process or sleep is involved. It lists `echo` and
    answers each call with the call's arguments as JSON."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.reader: asyncio.StreamReader | None = None
        self.calls = 0
        self.opened = 0

    async def open(self) -> tuple[asyncio.StreamReader, Callable[[str], Awaitable[None]]]:
        self.opened += 1
        self.reader = asyncio.StreamReader()
        return self.reader, self.write_line

    async def write_line(self, line: str) -> None:
        message = json.loads(line)
        if "id" not in message:
            return
        params = message.get("params") or {}
        result: dict[str, Any]
        if message["method"] == "initialize":
            result = {"protocolVersion": params["protocolVersion"]}
        elif message["method"] == "tools/list":
            result = {"tools": [{"name": "echo", "description": "Echo.", "inputSchema": {}}]}
        else:
            self.calls += 1
            text = json.dumps(params.get("arguments"), sort_keys=True)
            result = {"content": [{"type": "text", "text": text}]}
        reply = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        assert self.reader is not None
        self.reader.feed_data((json.dumps(reply) + "\n").encode())

    async def close(self, grace_seconds: float) -> None:
        del grace_seconds
        if self.reader is not None and not self.reader.at_eof():
            self.reader.feed_eof()

    def describe(self) -> str:
        return f"MCP server {self.name!r} (https example.test)"


class MemoryTransports:
    """A transport factory whose every server is one `MemoryMcpServer` per name."""

    def __init__(self) -> None:
        self.servers: dict[str, MemoryMcpServer] = {}

    def for_spec(self, server: McpServerSpec) -> MemoryMcpServer:
        if server.trust == "remote" and server.url is None:
            raise ValueError(f"MCP server {server.name!r} is remote but has no URL")
        return self.servers.setdefault(server.name, MemoryMcpServer(server.name))


class MemoryDocumentStore:
    """A document store that hands back one document held in memory, or raises `error`: a
    document no real reader would accept (one at the bundle's caps) without a byte on disk."""

    def __init__(
        self, document: SnapshotDocument | None = None, error: BaseException | None = None
    ) -> None:
        self.document = document
        self.error = error
        self.read_paths: list[Path] = []

    def write(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        raise AssertionError("a runner never writes its capability document")

    def rewrite(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        raise AssertionError("a runner never rewrites its capability document")

    def read(self, path: Path) -> SnapshotDocumentInterface:
        self.read_paths.append(path)
        if self.error is not None:
            raise self.error
        assert self.document is not None
        return self.document


class MemorySkillIndex:
    """`skills` per plugin folder name, `(name, description)`, as if read from SKILL.md files."""

    def __init__(self, skills: Mapping[str, Sequence[tuple[str, str]]]) -> None:
        self._skills = skills

    def build(self, plugin_dirs: Sequence[Path]) -> SkillCatalog:
        return SkillCatalog(
            tuple(
                SkillEntry(folder.name, name, description, folder / "skills" / name / "SKILL.md")
                for folder in plugin_dirs
                for name, description in self._skills.get(folder.name, ())
            ),
            (),
        )


class MemoryCommandIndex:
    """`commands` per plugin folder name, `(name, description)`, as if read from commands/."""

    def __init__(self, commands: Mapping[str, Sequence[tuple[str, str]]]) -> None:
        self._commands = commands

    def build(
        self, plugin_dirs: Sequence[Path]
    ) -> tuple[tuple[CommandEntry, ...], tuple[tuple[Path, str], ...]]:
        return (
            tuple(
                CommandEntry(folder.name, name, description, folder / "commands" / f"{name}.md")
                for folder in plugin_dirs
                for name, description in self._commands.get(folder.name, ())
            ),
            (),
        )


def memory_document(
    *,
    plugins: Sequence[str] = (),
    skills: Sequence[str] = (),
    mcp_servers: Sequence[McpServerSpec] = (),
    folders: Sequence[Path] = (),
    instruction_files: Sequence[str] = DEFAULT_INSTRUCTION_FILES,
    instruction_max_bytes: int = DEFAULT_INSTRUCTION_MAX_BYTES,
    capability_prompt_tokens: int = DEFAULT_CAPABILITY_PROMPT_TOKENS,
    capability_answer_tokens: int = DEFAULT_CAPABILITY_ANSWER_TOKENS,
) -> SnapshotDocument:
    """A version-2 document held in memory, its plugins under `/snapshot/plugins/`. A
    module-level builder: test data, with no state to hold."""
    return SnapshotDocument(
        version=DOCUMENT_VERSION,
        digest=MEMORY_DIGEST,
        plugin_dirs=tuple(Path("/snapshot/plugins") / name for name in plugins),
        skills=tuple(skills),
        mcp_servers=tuple(mcp_servers),
        builtin_web=False,
        instruction_files=tuple(instruction_files),
        instruction_max_bytes=instruction_max_bytes,
        capability_prompt_tokens=capability_prompt_tokens,
        capability_answer_tokens=capability_answer_tokens,
        folders=tuple(folders),
    )


class CapabilityDocumentWriter:
    """One run folder (0700) under `root`, its plugin copies, and the document beside them,
    written the way the conductor writes it (SP-LOOPS Phase 4, Task 2)."""

    def __init__(self, root: Path) -> None:
        self.run = Path(os.path.realpath(root)) / "snapshots" / "run-1"
        self.run.mkdir(parents=True)
        self.run.chmod(0o700)
        self.plugin_dirs: list[Path] = []

    def plugin(
        self,
        name: str,
        skills: Mapping[str, str] | None = None,
        commands: Mapping[str, str] | None = None,
    ) -> Path:
        """A plugin copy named `name` with `skills` and `commands` (name: description)."""
        folder = self.run / "plugins" / name
        (folder / ".claude-plugin").mkdir(parents=True)
        (folder / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": name}), encoding="utf-8"
        )
        for skill, description in (skills or {}).items():
            (folder / "skills" / skill).mkdir(parents=True)
            (folder / "skills" / skill / "SKILL.md").write_text(
                f"---\nname: {skill}\ndescription: {description}\n---\n\n# {skill}\n", "utf-8"
            )
        for command, description in (commands or {}).items():
            (folder / "commands").mkdir(exist_ok=True)
            (folder / "commands" / f"{command}.md").write_text(
                f"---\ndescription: {description}\n---\nRun {command}.\n", "utf-8"
            )
        self.plugin_dirs.append(folder)
        return folder

    def copy(self, source: Path) -> Path:
        """A copy of the plugin at `source`, as the conductor copies one into the run."""
        folder = self.run / "plugins" / source.name
        shutil.copytree(source, folder)
        self.plugin_dirs.append(folder)
        return folder

    def write(
        self,
        *,
        mcp_servers: Sequence[McpServerSpec] = (),
        folders: Sequence[Path] = (),
        instruction_files: Sequence[str] = DEFAULT_INSTRUCTION_FILES,
        capability_prompt_tokens: int = DEFAULT_CAPABILITY_PROMPT_TOKENS,
        capability_answer_tokens: int = DEFAULT_CAPABILITY_ANSWER_TOKENS,
    ) -> Path:
        """The document naming every skill the plugin copies hold, in index order."""
        catalog = SkillIndex().build(self.plugin_dirs)
        document = SnapshotDocument(
            version=DOCUMENT_VERSION,
            digest=MEMORY_DIGEST,
            plugin_dirs=tuple(self.plugin_dirs),
            skills=tuple(f"{entry.plugin}:{entry.name}" for entry in catalog.skills),
            mcp_servers=tuple(mcp_servers),
            builtin_web=False,
            instruction_files=tuple(instruction_files),
            instruction_max_bytes=DEFAULT_INSTRUCTION_MAX_BYTES,
            capability_prompt_tokens=capability_prompt_tokens,
            capability_answer_tokens=capability_answer_tokens,
            folders=tuple(folders),
        )
        return SnapshotDocumentStore().write(document, self.run)


assert isinstance(FakeOllamaProbe(), OllamaProbeInterface)
assert isinstance(MemoryMcpServer("x"), McpTransportInterface)
assert isinstance(MemoryTransports(), McpTransportFactoryInterface)
assert isinstance(MemoryDocumentStore(), SnapshotDocumentStoreInterface)
assert isinstance(MemorySkillIndex({}), SkillIndexInterface)
assert isinstance(MemoryCommandIndex({}), PluginCommandIndexInterface)
