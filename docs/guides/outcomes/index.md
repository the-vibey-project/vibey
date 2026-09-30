---
description: Six short guides, each answering one question people bring to AI coding agents, with the commands, the evidence behind every claim, and the limits.
---

# What do you want to do?

You probably arrived with a problem rather than a wish to learn a new tool: code that must
not leave your machine, an agent bill nobody can explain, an auditor asking what the agent
did. Each guide below answers one such question. It opens with a one-sentence answer, then
gives the commands, then links the code, tests and decisions that prove each claim, then
says plainly where vibey stops. Each reads in under five minutes.

## Use it

- **[How do I run AI coding agents entirely on my own hardware?](run-agents-on-your-own-hardware.md)**
  Run vibey on its default engine, GPT-OSS 20B on Ollama, and allow only that engine; the
  queue, the ledger and the model then stay on one machine.
- **[How do I cap what AI coding agents spend, and see where the money went?](cap-agent-spending.md)**
  Set a per-cycle dollar or turn cap with `vibey budget set`; the brake parks a gate when
  it trips, and `vibey cost` shows each engine's spend.

## Run it for a team

- **[How do I keep a tamper-evident record of everything an AI agent did?](keep-a-tamper-evident-record.md)**
  Every decision, answer, handoff and cost goes into a PostgreSQL ledger the application
  cannot rewrite, and each export walks a SHA-256 chain over it.
- **[How do I review an AI-built change before it can merge?](review-ai-changes-before-merge.md)**
  A REVIEW gate waits for your verdict, and vibey-gh merges a pull request only on checks
  that passed on its exact head commit.
- **[Can an AI agent deploy my software without holding cloud secrets?](deploy-without-storing-secrets.md)**
  Partly, and not yet for production: the opt-in Azure stages keep no credential and
  change nothing until you consent, but they are not yet proven against real Azure.

## Assess it

- **[Can I use vibey in a regulated environment?](take-vibey-into-a-regulated-environment.md)**
  A checklist of the mechanisms an assessor asks about, each with its evidence, and a plain
  list of what vibey does not provide. It is not a certification.

## Your question is not here?

Ask it in [Discussions](https://github.com/the-vibey-project/vibey/discussions). A
question two people ask is a guide worth writing, and writing one is a good first
contribution: copy the shape of any page above, and follow
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
from a fork to a pull request. [ADR-0077](../../architecture/decisions/0077-outcome-guides-answer-the-questions-users-search-for.md)
says what every guide must contain.
