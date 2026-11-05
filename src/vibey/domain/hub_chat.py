# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's chat command parser and turn renderer (ADR-0100).

Every krypton chat surface -- the GTK4/libadwaita desktop app, the iOS/Android/web Expo app,
and the VS Code chat participant -- speaks to the same `/api/v1/chat/messages` endpoint and
renders the same structured turn:

- `reply`: plain-text assistant summary of what ran and what needs attention;
- `tool_calls`: the `vibey_*` tool invocations (`name`, `arguments`, `result`) that ran;
- `gates`: open human gates formatted for inline approval cards (`is_spend`, `requires_scope`);
- `project_id`: the active project UUID in context, if any.

Pure: no I/O, no clock, no network. Declared by `interfaces/hub_chat_interface.py`.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal
from uuid import UUID

from vibey.domain.errors import LifecycleInvalid
from vibey.domain.host_tools import UUID_RE
from vibey.domain.hub_scope import SPEND_GATE_KINDS
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface

MAX_CHAT_MESSAGE_CHARS: Final = 4_000

IntentKind = Literal[
    "help",
    "projects",
    "status",
    "gates",
    "answer_gate",
    "budget",
    "queue",
    "ledger",
    "loops",
    "lanes",
    "doctor",
    "start_project",
    "start_work",
    "pause_work",
    "abandon_project",
]

VERDICT_GATE_KINDS: Final[frozenset[str]] = frozenset({"approval", "deploy_demo_review"})
CHOICE_GATE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "choice",
        "deploy_interview",
        "deploy_failure_triage",
        "bus_dead_lettered",
        "deploy_acceptance",
    }
)
GRANT_GATE_KEYS: Final[Mapping[str, str]] = {
    "budget_exhausted": "max_dollars",
    "escalation_exhausted": "max_attempts",
    "attempts_exhausted": "max_attempts",
    "verify_repair_exhausted": "max_rounds",
    "integrate_repair_exhausted": "max_rounds",
}
ANY_ANSWER_GATE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "delivery_exhausted",
        "research_evidence",
        "engine_misconfigured",
        "ultra_needs_cap",
    }
)

SLUG_WORDS_RE: Final = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class ChatSlashSpec:
    slash: str
    usage: str
    title: str
    description: str
    tool_name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "slash": self.slash,
            "usage": self.usage,
            "title": self.title,
            "description": self.description,
            "tool_name": self.tool_name,
        }


@dataclass(frozen=True, slots=True)
class ChatIntent:
    kind: IntentKind
    tool_name: str | None = None
    project_id: UUID | None = None
    gate_id: UUID | None = None
    answer: Mapping[str, Any] | None = None
    raw_answer: str | None = None
    name: str | None = None
    intake: str = ""
    text: str | None = None
    reason: str = ""
    dry_run: bool = True


CHAT_SLASH_COMMANDS: Final[tuple[ChatSlashSpec, ...]] = (
    ChatSlashSpec(
        slash="projects",
        usage="/projects",
        title="List projects",
        description="List every project on this hub with its phase and open gate count.",
        tool_name="vibey_projects",
    ),
    ChatSlashSpec(
        slash="status",
        usage="/status [project-id]",
        title="Project status",
        description="Show a project's phase, cycle, queue depth and engine circuits.",
        tool_name="vibey_status",
    ),
    ChatSlashSpec(
        slash="gates",
        usage="/gates [project-id]",
        title="Open gates",
        description="List open human gates waiting for your answer.",
        tool_name="vibey_gates",
    ),
    ChatSlashSpec(
        slash="answer",
        usage="/answer <gate-id> <choice|json>",
        title="Answer a gate",
        description="Answer an open human gate once.",
        tool_name="vibey_answer_gate",
    ),
    ChatSlashSpec(
        slash="budget",
        usage="/budget [project-id]",
        title="Project budget",
        description="Show a project's budget caps and spend (read-only).",
        tool_name="vibey_budget",
    ),
    ChatSlashSpec(
        slash="queue",
        usage="/queue [project-id]",
        title="Project queue",
        description="List a project's queued and running jobs in claim order.",
        tool_name="vibey_queue",
    ),
    ChatSlashSpec(
        slash="ledger",
        usage="/ledger [project-id] [search text]",
        title="Search ledger",
        description="Search a project's append-only ledger events.",
        tool_name="vibey_ledger",
    ),
    ChatSlashSpec(
        slash="loops",
        usage="/loops",
        title="Loops and engines",
        description="Show the configured loops, engines and effort levels.",
        tool_name="vibey_loops",
    ),
    ChatSlashSpec(
        slash="lanes",
        usage="/lanes",
        title="Active lanes",
        description="List the runner lanes active on this computer.",
        tool_name="vibey_lanes",
    ),
    ChatSlashSpec(
        slash="doctor",
        usage="/doctor",
        title="Hub health checks",
        description="Run the hub's self-checks.",
        tool_name="vibey_doctor",
    ),
    ChatSlashSpec(
        slash="new",
        usage="/new <name> <what to build>",
        title="Start a project",
        description="Create and enqueue a new project on the host.",
        tool_name="vibey_start_project",
    ),
    ChatSlashSpec(
        slash="start",
        usage="/start [project-id]",
        title="Resume project worker",
        description="Start or resume a project's worker.",
        tool_name="vibey_start_work",
    ),
    ChatSlashSpec(
        slash="pause",
        usage="/pause [project-id]",
        title="Pause project worker",
        description="Stop a project's own workers.",
        tool_name="vibey_pause_work",
    ),
    ChatSlashSpec(
        slash="abandon",
        usage="/abandon [project-id] [--confirm] <reason>",
        title="Unwind a project",
        description="Preview (or with --confirm, execute) unwinding a project.",
        tool_name="vibey_abandon_project",
    ),
    ChatSlashSpec(
        slash="help",
        usage="/help",
        title="Show chat commands",
        description="List every slash command and conversational shortcut.",
        tool_name=None,
    ),
)


class HubChat(HubChatInterface):
    """Parses operator chat messages into hub tool calls and renders turn responses.

    Declared by `interfaces/hub_chat_interface.py::HubChatInterface`."""

    def slash_commands(self) -> tuple[ChatSlashSpec, ...]:
        return CHAT_SLASH_COMMANDS

    def help_text(self) -> str:
        lines = [
            "Commands you can type in chat (or ask in plain words):",
            *(f"  {spec.usage:<40} {spec.description}" for spec in CHAT_SLASH_COMMANDS),
            "",
            "Tip: Select a project in the sidebar so commands like `/status`, `/gates`, `/budget` "
            "and `/queue` use it automatically, or type a bare option number (`1`, `2`, ...) to "
            "answer the oldest open gate.",
        ]
        return "\n".join(lines)

    def parse(
        self,
        message: str,
        *,
        project_id: UUID | None = None,
        open_gates: Sequence[Mapping[str, Any]] = (),
    ) -> ChatIntent:
        cleaned = message.strip()
        if not cleaned:
            raise LifecycleInvalid("write a message or a /command")
        if len(cleaned) > MAX_CHAT_MESSAGE_CHARS:
            raise LifecycleInvalid(f"a chat message is at most {MAX_CHAT_MESSAGE_CHARS} characters")
        if cleaned.startswith("/"):
            return self._parse_slash(cleaned, project_id=project_id, open_gates=open_gates)
        return self._parse_natural(cleaned, project_id=project_id, open_gates=open_gates)

    def parse_gate_answer(self, kind: str, raw: str) -> dict[str, Any]:
        token = raw.strip()
        if token.startswith("{"):
            try:
                parsed: dict[str, Any] = json.loads(token)
            except json.JSONDecodeError as exc:
                raise LifecycleInvalid("write the gate answer as a valid JSON object") from exc
            return parsed
        if kind == "question":
            if token in ("", "--defaults", "defaults", "accept", "yes", "ok"):
                return {"accept_defaults": True}
            raise LifecycleInvalid(
                "answer a design question gate with `defaults` or a JSON object of answers"
            )
        if kind in VERDICT_GATE_KINDS:
            if not token:
                raise LifecycleInvalid("choose one of the gate's verdict options")
            return {"verdict": token}
        if kind in CHOICE_GATE_KINDS:
            if not token:
                raise LifecycleInvalid("choose one of the gate's options")
            return {"choice": token}
        if kind in GRANT_GATE_KEYS:
            key = GRANT_GATE_KEYS[kind]
            try:
                bound = float(token)
            except ValueError as exc:
                raise LifecycleInvalid(f"a new {key} is a non-negative number") from exc
            if not math.isfinite(bound) or bound < 0:
                raise LifecycleInvalid(f"a new {key} is a non-negative number")
            value: int | float = int(bound) if bound.is_integer() else bound
            return {key: value}
        if kind in ANY_ANSWER_GATE_KINDS:
            return {}
        raise LifecycleInvalid("write the gate answer as a JSON object")

    def format_gate_prompt(self, gate: Mapping[str, Any]) -> dict[str, Any]:
        kind = str(gate.get("kind", ""))
        is_spend = kind in SPEND_GATE_KINDS
        grant_key = GRANT_GATE_KEYS.get(kind)
        return {
            **dict(gate),
            "is_spend": is_spend,
            "requires_scope": "spend" if is_spend else "answer",
            "grant_key": grant_key,
        }

    def summarize_turn(
        self,
        *,
        intent: ChatIntent,
        tool_calls: Sequence[Mapping[str, Any]],
        gates: Sequence[Mapping[str, Any]],
        project_id: UUID | None,
    ) -> dict[str, Any]:
        formatted_gates = [self.format_gate_prompt(g) for g in gates]
        reply = self._render_reply(intent, tool_calls, formatted_gates)
        return {
            "reply": reply,
            "tool_calls": [dict(call) for call in tool_calls],
            "gates": formatted_gates,
            "project_id": str(project_id) if project_id is not None else None,
        }

    def _parse_slash(
        self,
        cleaned: str,
        *,
        project_id: UUID | None,
        open_gates: Sequence[Mapping[str, Any]],
    ) -> ChatIntent:
        parts = cleaned[1:].split(None, 1)
        cmd = parts[0].lower() if parts else "help"
        rest = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("help", "?"):
            return ChatIntent(kind="help", project_id=project_id)
        if cmd == "projects":
            return ChatIntent(kind="projects", tool_name="vibey_projects", project_id=project_id)
        if cmd == "loops":
            return ChatIntent(kind="loops", tool_name="vibey_loops", project_id=project_id)
        if cmd == "lanes":
            return ChatIntent(kind="lanes", tool_name="vibey_lanes", project_id=project_id)
        if cmd == "doctor":
            return ChatIntent(kind="doctor", tool_name="vibey_doctor", project_id=project_id)
        if cmd == "gates":
            target = self._optional_uuid(rest, fallback=project_id)
            return ChatIntent(kind="gates", tool_name="vibey_gates", project_id=target)
        if cmd == "status":
            target = self._require_uuid(rest, fallback=project_id, command="/status")
            return ChatIntent(kind="status", tool_name="vibey_status", project_id=target)
        if cmd == "budget":
            target = self._require_uuid(rest, fallback=project_id, command="/budget")
            return ChatIntent(kind="budget", tool_name="vibey_budget", project_id=target)
        if cmd == "queue":
            target = self._require_uuid(rest, fallback=project_id, command="/queue")
            return ChatIntent(kind="queue", tool_name="vibey_queue", project_id=target)
        if cmd == "start":
            target = self._require_uuid(rest, fallback=project_id, command="/start")
            return ChatIntent(kind="start_work", tool_name="vibey_start_work", project_id=target)
        if cmd in ("pause", "stop"):
            target = self._require_uuid(rest, fallback=project_id, command="/pause")
            return ChatIntent(kind="pause_work", tool_name="vibey_pause_work", project_id=target)
        if cmd == "ledger":
            return self._parse_ledger(rest, fallback=project_id)
        if cmd in ("answer", "reply"):
            return self._parse_answer_slash(rest, project_id=project_id, open_gates=open_gates)
        if cmd in ("new", "ask"):
            return self._parse_new_slash(rest, is_ask=(cmd == "ask"))
        if cmd == "abandon":
            return self._parse_abandon_slash(rest, fallback=project_id)
        raise LifecycleInvalid(f"unknown command `/{cmd}`; type `/help` to list every command")

    def _parse_ledger(self, rest: str, *, fallback: UUID | None) -> ChatIntent:
        if not rest:
            target = self._require_uuid("", fallback=fallback, command="/ledger")
            return ChatIntent(kind="ledger", tool_name="vibey_ledger", project_id=target, text=None)
        tokens = rest.split(None, 1)
        first = tokens[0]
        if UUID_RE.fullmatch(first):
            target = UUID(first)
            query_text = tokens[1].strip() if len(tokens) > 1 else None
            return ChatIntent(
                kind="ledger",
                tool_name="vibey_ledger",
                project_id=target,
                text=query_text or None,
            )
        target = self._require_uuid("", fallback=fallback, command="/ledger")
        return ChatIntent(kind="ledger", tool_name="vibey_ledger", project_id=target, text=rest)

    def _parse_answer_slash(
        self,
        rest: str,
        *,
        project_id: UUID | None,
        open_gates: Sequence[Mapping[str, Any]],
    ) -> ChatIntent:
        if not rest:
            raise LifecycleInvalid("usage: `/answer <gate-id> <choice|json>`")
        tokens = rest.split(None, 1)
        first = tokens[0]
        if UUID_RE.fullmatch(first):
            if len(tokens) < 2 or not tokens[1].strip():
                raise LifecycleInvalid("usage: `/answer <gate-id> <choice|json>`")
            gate_id = UUID(first)
            raw = tokens[1].strip()
            matched = next((g for g in open_gates if str(g.get("gate_id")) == str(gate_id)), None)
            if matched is not None:
                answer = self.parse_gate_answer(str(matched.get("kind", "")), raw)
                return ChatIntent(
                    kind="answer_gate",
                    tool_name="vibey_answer_gate",
                    project_id=project_id,
                    gate_id=gate_id,
                    answer=answer,
                    raw_answer=raw,
                )
            return ChatIntent(
                kind="answer_gate",
                tool_name="vibey_answer_gate",
                project_id=project_id,
                gate_id=gate_id,
                raw_answer=raw,
            )
        if len(open_gates) == 1:
            only = open_gates[0]
            gate_id = UUID(str(only["gate_id"]))
            kind = str(only.get("kind", ""))
            options = list(only.get("options") or ())
            raw = rest
            if first.isdigit() and len(tokens) == 1:
                idx = int(first) - 1
                if 0 <= idx < len(options):
                    raw = str(options[idx])
            answer = self.parse_gate_answer(kind, raw)
            return ChatIntent(
                kind="answer_gate",
                tool_name="vibey_answer_gate",
                project_id=project_id,
                gate_id=gate_id,
                answer=answer,
                raw_answer=raw,
            )
        raise LifecycleInvalid("specify which gate UUID to answer: `/answer <gate-id> <answer>`")

    def _parse_new_slash(self, rest: str, *, is_ask: bool) -> ChatIntent:
        if not rest:
            raise LifecycleInvalid("usage: `/new <project-name> <what to build>`")
        if is_ask:
            slug = self._derive_slug(rest)
            return ChatIntent(
                kind="start_project",
                tool_name="vibey_start_project",
                name=slug,
                intake=rest,
            )
        tokens = rest.split(None, 1)
        name = tokens[0]
        intake = tokens[1].strip() if len(tokens) > 1 else ""
        return ChatIntent(
            kind="start_project",
            tool_name="vibey_start_project",
            name=name,
            intake=intake,
        )

    def _parse_abandon_slash(self, rest: str, *, fallback: UUID | None) -> ChatIntent:
        parts = rest.split()
        dry_run = True
        filtered: list[str] = []
        for part in parts:
            if part == "--confirm":
                dry_run = False
            elif part == "--dry-run":
                dry_run = True
            else:
                filtered.append(part)
        target = fallback
        if filtered and UUID_RE.fullmatch(filtered[0]):
            target = UUID(filtered[0])
            filtered = filtered[1:]
        if target is None:
            raise LifecycleInvalid(
                "select a project or pass its UUID: `/abandon <project-id> <reason>`"
            )
        reason = " ".join(filtered).strip()
        if not reason:
            raise LifecycleInvalid("give a reason: `/abandon <project-id> <reason>`")
        return ChatIntent(
            kind="abandon_project",
            tool_name="vibey_abandon_project",
            project_id=target,
            reason=reason,
            dry_run=dry_run,
        )

    def _parse_natural(
        self,
        cleaned: str,
        *,
        project_id: UUID | None,
        open_gates: Sequence[Mapping[str, Any]],
    ) -> ChatIntent:
        lower = cleaned.lower()
        if lower in ("help", "?", "commands", "what can you do", "what can you do?"):
            return ChatIntent(kind="help", project_id=project_id)
        if open_gates and cleaned.isdigit():
            only = open_gates[0]
            options = list(only.get("options") or ())
            idx = int(cleaned) - 1
            if 0 <= idx < len(options):
                choice = str(options[idx])
                answer = self.parse_gate_answer(str(only.get("kind", "")), choice)
                return ChatIntent(
                    kind="answer_gate",
                    tool_name="vibey_answer_gate",
                    project_id=project_id,
                    gate_id=UUID(str(only["gate_id"])),
                    answer=answer,
                    raw_answer=choice,
                )
        if lower in ("projects", "list projects", "show projects"):
            return ChatIntent(kind="projects", tool_name="vibey_projects", project_id=project_id)
        if lower in ("gates", "open gates", "list gates", "show gates"):
            return ChatIntent(kind="gates", tool_name="vibey_gates", project_id=project_id)
        if lower in ("loops", "list loops", "show loops", "engines"):
            return ChatIntent(kind="loops", tool_name="vibey_loops", project_id=project_id)
        if lower in ("lanes", "list lanes", "show lanes", "running lanes"):
            return ChatIntent(kind="lanes", tool_name="vibey_lanes", project_id=project_id)
        if lower in ("doctor", "health", "check health"):
            return ChatIntent(kind="doctor", tool_name="vibey_doctor", project_id=project_id)
        if lower in ("status", "project status", "how is it going", "how is it going?"):
            if project_id is None:
                return ChatIntent(kind="projects", tool_name="vibey_projects", project_id=None)
            return ChatIntent(kind="status", tool_name="vibey_status", project_id=project_id)
        if lower in ("budget", "spend", "caps", "show budget"):
            target = self._require_uuid("", fallback=project_id, command="/budget")
            return ChatIntent(kind="budget", tool_name="vibey_budget", project_id=target)
        if lower in ("queue", "jobs", "show queue"):
            target = self._require_uuid("", fallback=project_id, command="/queue")
            return ChatIntent(kind="queue", tool_name="vibey_queue", project_id=target)
        if lower in ("pause", "stop", "pause work"):
            target = self._require_uuid("", fallback=project_id, command="/pause")
            return ChatIntent(kind="pause_work", tool_name="vibey_pause_work", project_id=target)
        if lower in ("start", "resume", "start work", "resume work"):
            target = self._require_uuid("", fallback=project_id, command="/start")
            return ChatIntent(kind="start_work", tool_name="vibey_start_work", project_id=target)
        if project_id is not None:
            return ChatIntent(kind="status", tool_name="vibey_status", project_id=project_id)
        return ChatIntent(kind="projects", tool_name="vibey_projects", project_id=None)

    @staticmethod
    def _optional_uuid(token: str, *, fallback: UUID | None) -> UUID | None:
        stripped = token.strip()
        if not stripped:
            return fallback
        if not UUID_RE.fullmatch(stripped):
            raise LifecycleInvalid(f"`{stripped}` is not a valid UUID")
        return UUID(stripped)

    @staticmethod
    def _require_uuid(token: str, *, fallback: UUID | None, command: str) -> UUID:
        stripped = token.strip()
        if stripped:
            if not UUID_RE.fullmatch(stripped):
                raise LifecycleInvalid(f"`{stripped}` is not a valid UUID")
            return UUID(stripped)
        if fallback is not None:
            return fallback
        raise LifecycleInvalid(f"select a project first or pass its UUID: `{command} <project-id>`")

    @staticmethod
    def _derive_slug(text: str) -> str:
        words = SLUG_WORDS_RE.findall(text.lower())[:4]
        if not words:
            return "task"
        slug = "-".join(words)[:48].strip("-")
        return slug or "task"

    def _render_reply(
        self,
        intent: ChatIntent,
        tool_calls: Sequence[Mapping[str, Any]],
        gates: Sequence[Mapping[str, Any]],
    ) -> str:
        if intent.kind == "help":
            return self.help_text()
        if not tool_calls:
            return "Done."
        first = tool_calls[0]
        result = first.get("result")
        if intent.kind == "projects" and isinstance(result, Sequence):
            if not result:
                return "No projects yet. Type `/new <name> <what to build>` to start one."
            lines = [f"{len(result)} project(s):"]
            for item in result:
                if isinstance(item, Mapping):
                    name = item.get("name", "?")
                    phase = item.get("phase", "?")
                    open_count = item.get("open_gates", 0)
                    gate_note = f" ({open_count} open gate(s))" if open_count else ""
                    lines.append(f"- {name} [{phase}]{gate_note}")
            return "\n".join(lines)
        if intent.kind == "status" and isinstance(result, Mapping):
            project = result.get("project")
            proj_map = project if isinstance(project, Mapping) else result
            name = proj_map.get("name", "project")
            phase = proj_map.get("phase", "?")
            cycle = proj_map.get("cycle", "?")
            gate_suffix = f" — {len(gates)} open gate(s)." if gates else "."
            return f"{name} is in {phase} (cycle {cycle}){gate_suffix}"
        if intent.kind == "gates":
            if not gates:
                return "No open human gates."
            lines = [f"{len(gates)} open gate(s):"]
            for idx, gate in enumerate(gates, start=1):
                badge = " [SPEND GATE — requires spend scope]" if gate.get("is_spend") else ""
                prompt = gate.get("prompt", "")
                kind = gate.get("kind", "gate")
                lines.append(f"{idx}. [{kind}]{badge} {prompt}")
            return "\n".join(lines)
        if intent.kind == "answer_gate" and isinstance(result, Mapping):
            replayed = " (replayed)" if result.get("replayed") else ""
            return f"Answered gate {result.get('gate_id', intent.gate_id)}{replayed}."
        if intent.kind == "budget" and isinstance(result, Mapping):
            spent = result.get("dollars_spent", 0)
            cap = result.get("max_dollars")
            cap_str = f" / ${cap}" if cap is not None else " (no dollar cap)"
            return f"Spend: ${spent}{cap_str}."
        if intent.kind == "queue" and isinstance(result, Mapping):
            entries = result.get("entries")
            count = len(entries) if isinstance(entries, Sequence) else 0
            return f"{count} job(s) in the queue."
        if intent.kind == "ledger" and isinstance(result, Mapping):
            events = result.get("events")
            count = len(events) if isinstance(events, Sequence) else 0
            return f"Found {count} ledger event(s)."
        if intent.kind == "loops" and isinstance(result, Mapping):
            loops = result.get("loops")
            count = len(loops) if isinstance(loops, Sequence) else 0
            return f"{count} loop(s) configured."
        if intent.kind == "lanes" and isinstance(result, Mapping):
            lanes = result.get("lanes")
            count = len(lanes) if isinstance(lanes, Sequence) else 0
            return f"{count} active lane(s) on this computer."
        if intent.kind == "doctor" and isinstance(result, Mapping):
            checks = result.get("checks")
            if isinstance(checks, Sequence):
                summary = ", ".join(
                    f"{c.get('name')}: {c.get('mark')}" for c in checks if isinstance(c, Mapping)
                )
                return f"Hub checks — {summary}."
        if intent.kind == "start_project" and isinstance(result, Mapping):
            return f"Started project `{result.get('name', intent.name)}` ({result.get('outcome', 'queued')})."
        if intent.kind in ("start_work", "pause_work") and isinstance(result, Mapping):
            return str(result.get("message") or "Updated project worker.")
        if intent.kind == "abandon_project" and isinstance(result, Mapping):
            if intent.dry_run:
                return "Dry run complete: review what would be unwound, then pass `--confirm` to execute."
            return "Project unwound."
        return "Done."


HUB_CHAT: Final = HubChat()
"""The default stateless chat command parser and turn renderer."""
