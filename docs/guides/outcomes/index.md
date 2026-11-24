---
description: Six short guides, each answering one question people bring to AI coding agents, with the commands, the evidence behind every claim, and the limits.
---

# What do you want to do?

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** Six guides, one per question people bring to AI coding
> agents: code that must stay on your machine, a bill nobody can explain, an auditor asking what
> the agent did. Pick your question below; each guide answers in one sentence, then gives the
> commands, the evidence and the limits, in under five minutes. vibey is 0.4.0, pre-1.0 and
> under active development; notices go to the [Discord server](https://discord.gg/Qvu8aYnVS).

Need vibey first? One command installs it and its runners on macOS or Linux, fetching uv and
Python 3.12 if they are missing:

```bash
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
```

It does not set up PostgreSQL 14 or later, the database, Ollama or the model; `vibey doctor`,
which it runs last, lists what is still missing. [Install](../install.md) walks through the
rest and every krypton app, and [Downloads](../downloads.md) has the files. To drive vibey from
Claude Code, Codex, Cursor, VS Code, Claude Desktop, Gemini CLI (over MCP) or Zed (over ACP),
see `vibey connect` in the [ACP guide](../acp.md).

## The lesson: start from the problem

Daniel had three browser tabs of agent frameworks open and had read none of them to the end.

**Daniel:** Where do I start? There is so much to learn.

**Professor Feynman:** Don't start with the tool. Start with what is bothering you. A carpenter
does not learn every tool in the shop; he learns the one that fixes the door that sticks.

**Daniel:** My door is that the code can't leave the building.

**Professor Feynman:** Then read one guide, the first below, and stop. Each page answers one
question, shows the commands, links the test or decision behind every claim, and ends with what
vibey does not do. The picture stops working in one place: these doors share a frame. The ledger
and the gates turn up in every guide, so the second one you read goes faster.

## Use it

- **[How do I run AI coding agents entirely on my own hardware?](run-agents-on-your-own-hardware.md)**
  Run the default engine on the Heretic v2 build of GPT-OSS 20B in Ollama and allow no other;
  the queue, the ledger and the model stay on one machine, and web search can be shut off too.
- **[How do I cap what AI coding agents spend, and see where the money went?](cap-agent-spending.md)**
  Set a per-cycle dollar or turn cap with `vibey budget set`; the brake parks a gate when it
  trips, only the host or a device holding `spend` may say yes, and `vibey cost` shows each
  engine's spend.

## Run it for a team

- **[How do I keep a tamper-evident record of everything an AI agent did?](keep-a-tamper-evident-record.md)**
  Every decision, answer, handoff and cost goes into a PostgreSQL ledger the application
  cannot rewrite, and each export walks a SHA-256 chain over it.
- **[How do I review an AI-built change before it can merge?](review-ai-changes-before-merge.md)**
  A REVIEW gate waits for your verdict, vibey can open a draft pull request when you declare
  `[publish]`, and vibey-gh merges only on checks that passed on the exact head commit.
- **[Can an AI agent deploy my software without holding cloud secrets?](deploy-without-storing-secrets.md)**
  Partly, and not yet for production: the opt-in Azure stages keep no credential and change
  nothing until you consent, but they are not yet proven against real Azure, and no other cloud
  is built.

## Assess it

- **[Can I use vibey in a regulated environment?](take-vibey-into-a-regulated-environment.md)**
  A checklist of the mechanisms an assessor asks about, each with its evidence, including the
  hub's scopes and the release attestations, and a plain list of what vibey does not provide.
  It is not a certification.

## Daniel's teach-back

**Daniel:** I pick the guide whose question is mine, read its one-sentence answer, run its
commands, and check its links when I need to believe a claim. Every guide ends with what vibey
does not do, so I read that part before I rely on it.

**Professor Feynman:** Good. And the guides are short on purpose: five minutes, not an afternoon.

## Your question is not here?

Ask it in [Discussions](https://github.com/the-vibey-project/vibey/discussions). A
question two people ask is a guide worth writing, and writing one is a good first
contribution: copy the shape of any page above, and follow
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
from a fork to a pull request. [ADR-0077](../../architecture/decisions/0077-outcome-guides-answer-the-questions-users-search-for.md)
says what every guide must contain.

## Where next

- [The non-profit demo](../demos/non-profit.md): the first two guides used together, on one
  small project.
- [How vibey survives a crashed agent](../../case-studies/how-vibey-survives-a-crashed-agent.md):
  why the queue and ledger behind every guide lose no work.

## Say it in one line

vibey's outcome guides answer one real question each, in under five minutes, with the commands, the evidence and the limits.
