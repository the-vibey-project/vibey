---
description: A walk-through for a small non-profit team that builds a volunteer shift sign-up tool on a local model with a spending brake, answers the questions only people can, and ends with a record a board can read.
---

# The non-profit demo: a volunteer sign-up tool, a budget you set, a machine you own

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For a small non-profit team with one person comfortable in a
> terminal and one computer with 24 GB of memory or more. You build a page where volunteers pick
> a shift, on a local model that costs nothing per token, with a spending cap as a backstop. Most
> of the setup time is a 12.1 GB model download. Afterwards you have the tool on a local branch
> and a record of every decision you can hand to a board. vibey is 0.4.0 and under active
> development; notices go to the [Discord server](https://discord.gg/Qvu8aYnVS).

Non-profits are the fifth of the six audiences vibey names, and the one whose demo was written
first ([ADR-0087](../../architecture/decisions/0087-the-six-audiences-in-order.md)). This page
follows one small, invented project from an empty machine to a finished build and a record you
can hand to someone else. The organisation is illustrative: nothing here describes a real team,
adopter or result.

**What vibey is, in one breath.** An AI coding agent writes software from plain-English
requests. vibey manages those agents like a project manager: it asks you questions first,
builds without you, checks the work, and writes every step to a record that can only be added
to.

## The lesson: the volunteer who never forgets

The church hall smelled of coffee, and the shift rota was pinned to a corkboard, half of it
crossed out.

**Daniel:** Our charity can't afford a developer, and I can't afford to babysit an AI.

**Professor Feynman:** Think of the best volunteer you ever had. She asks what you want before she
starts, she does the work while you are out, she checks it, and she writes everything in the
logbook so the next volunteer knows exactly where things stand.

**Daniel:** And she never sends the bill to someone else?

**Professor Feynman:** That is the point of running it on your own computer: the model costs
nothing per word. If you ever let a paid helper in, a cap stops the spending and asks you first.

**Daniel:** So I can just let it run.

**Professor Feynman:** Mostly. The questions that are yours, what the page must do and what it must
never show, wait for you. The picture stops working in one place: your best volunteer had
judgement. A local model is a capable apprentice, so a person still reads what matters.

## Before you start: the honest costs

- **A strong enough computer.** A Mac with 24 GB of memory or more, or a graphics card with
  about 16 GB (recommended, not yet verified); a 16 GB Mac cannot run the model
  ([hardware](../../reference/system-requirements.md#hardware)). If your team has no such
  machine, this demo is not yet for you, and that is a real gap.
- **About 12.1 GB to download once**, and about 20 GB of disk.
- **Someone comfortable in a terminal.** You type the commands below. vibey spares that person
  the babysitting; it does not replace them.
- **Software that is free but not costless.** The licence is MIT and local turns are priced at
  zero. Electricity, the machine and your volunteers' time are not.

## 1. Set it up once

Install vibey, PostgreSQL and Ollama, and pull the model: steps 1 and 2 of
[run agents on your own hardware](../outcomes/run-agents-on-your-own-hardware.md#steps). Keep
the two database roles they describe, because the record's protection depends on it.

```bash
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh
ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE
vibey doctor --sovereign-fit    # measures whether the model fits this machine
```

## 2. Start the project with a brake on it, and say what to build

```bash
vibey new shift-signup --repo ~/src/shift-signup \
  --intake "A web page where volunteers pick a shift from a weekly rota. Coordinators see who signed up; volunteers never see each other's phone numbers." \
  --max-cycle-dollars 15 --max-cycle-turns 200
```

The cap is a backstop. The first defence is the allow-list in step 4, which keeps paid agents
out altogether. The cap matters only if someone later allows one, and then it parks the work
and asks before spending more ([cap what agents spend](../outcomes/cap-agent-spending.md)).

## 3. Give the interview your own words

When vibey plans the design, it researches three topics: `prior-art`, `libraries` and
`api-docs`. Your own notes come first. Put your volunteer handbook, the list of shifts and
anything about who may see volunteers' details into a folder, as `prior-art.md`,
`libraries.md` and `api-docs.md`, each starting with a `source:` line. A topic with its file is
never searched for.

```bash
export VIBEY_EVIDENCE_DIR=~/notes/shift-signup
vibey doctor --engine gptossloop --conformance --record
```

The second command records that the local engine passed its checks; vibey uses no engine until
that has happened.

**About the web.** Without a file for a topic, vibey searches through a local SearXNG if one
runs, or Brave if you set a key, and reads a few result pages. If your volunteers' details must
never leave the building, follow [what leaves the machine, and how to stop it](../outcomes/run-agents-on-your-own-hardware.md#what-leaves-the-machine-and-how-to-stop-it):
no SearXNG, no Brave key, and `[web] allow_hosts = []`. Then a topic with no file parks a
question for you instead of searching.

To give every build run a file of its own, such as this term's rota, use run inputs
([ADR-0104](../../architecture/decisions/0104-run-inputs-hash-addressed.md)):

```bash
vibey inputs add PROJECT_ID --file ~/notes/shift-signup/rota.csv
vibey inputs list PROJECT_ID     # digest, kind, size and name; never the content
```

## 4. Build on the local model only

```bash
vibey worker --provider gptossloop --engines gptossloop
vibey gates        # in a second terminal: what is waiting for you
```

`vibey gates` prints each question with the exact `vibey answer` command that answers it. These
are your decisions: what the page must do, what it must never show. With the hub running
(`vibey hub start`), a krypton app paired with `vibey hub pair --scope view --scope answer` can
answer the same questions ([pairing](../../reference/hub-api.md#pairing)); a spending question
also needs `--scope spend`. When the interview is finished, accept the
design yourself:

```bash
vibey design accept PROJECT_ID --no-visual
```

Building then runs without you. You can stop the worker at any time: work lives in a queue and
the database, and a restarted worker picks up where the last one stopped.

## 5. Review it, and stop short of deploying

When the build is done, vibey parks two questions in turn: your verdict on the result, then
whether to deploy at all.

```bash
vibey answer GATE_ID --verdict accept
vibey answer GATE_ID --choice local_only
```

`local_only` is a complete finish, and the work stays on a local integration branch. This demo
stops here on purpose: the deployment stages are not yet proven against real cloud accounts
([deploy without holding cloud secrets](../outcomes/deploy-without-storing-secrets.md)).

## 6. Hand someone the record

```bash
vibey cost                                       # spend this cycle, per engine
vibey ledger show --limit 100                    # every decision and answer, in order
vibey ledger export PROJECT_ID -o ledger.jsonl   # a shard with its hash-chain head
```

On the all-local path `vibey cost` shows zero for every engine. Copy the exported file off the
machine, so the head cannot be rewritten by whoever can rewrite the database
([keep a tamper-evident record](../outcomes/keep-a-tamper-evident-record.md#steps)). What the
shard leaves out, and why, is in [what gets published](../ledger-publication.md).

## Daniel's teach-back

**Daniel:** I set up vibey, PostgreSQL and the local model once. I start the project with a
plain description and a cap, give the design interview our own notes, and run a worker that can
use only the local engine. I answer the questions that are ours, accept the review, finish
locally, and export the record for the board.

**Professor Feynman:** That is the whole walk. Remember the one door: without notes, the design
step looks things up on the web unless you shut it.

## The evidence

| Claim | Where it is proved |
|---|---|
| The default engine is local and runs on your hardware | [ADR-0064](../../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md) |
| The default model is the Heretic v2 build, 12.1 GB | [ADR-0099](../../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md) |
| `--engines` confines the worker, and local engines are chosen first | [ADR-0038](../../architecture/decisions/0038-local-engines-are-preferred-first.md) |
| A tripped cap parks a gate instead of spending | [ADR-0024](../../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md) |
| Your notes win, and web research is local-first | [ADR-0102](../../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md) |
| The ledger refuses edits and is exported with a chain head | [ADR-0055](../../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md) |
| Deployment needs your recorded consent | [ADR-0014](../../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md) |

## Limits

- **This walk-through has not been recorded end to end.** Each command was checked against its
  `vibey --help` on 2026-11-24, at `develop` commit `d91a3791e` (vibey 0.4.0), and each step's
  claims come from the guides linked above. A single unbroken run on one machine is not on
  record, so the demo describes what you will see and shows no output it did not capture.
- **The reviewer is the builder.** With one local engine, the check of each finished item is
  done by the engine that wrote it, and vibey records that weaker independence
  ([ADR-0035](../../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
  Have a person read what matters.
- **A local model is not a frontier model.** [The honest ceiling](../local-models-ollama.md#the-honest-ceiling)
  says what it can carry; expect to answer more questions and fix more by hand.
- **Your volunteers' data is yours to protect.** vibey keeps its own traffic on your machine
  once web research is shut. The app it builds, its hosting and what it stores are your
  responsibility, and vibey makes no claim about any privacy or charity law.
- **A funder may not accept the record.** vibey supplies a record and checks, not an audit, and
  the export has no verify command yet.
- **No grant, service or support comes with this.** It is a free tool and a guide.

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| `vibey doctor` says the model "is not served" | The model is not pulled | `ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` |
| A `research_evidence` question appears | A topic had no notes and no search answered | Add that topic's file, then answer the question |
| `cycle budget exhausted` | Someone allowed a paid engine and it hit the cap | Leave the gate unanswered to stop there, or raise the cap with `--raw '{"max_dollars": 25}'` |

## Where next

- [Run agents on your own hardware](../outcomes/run-agents-on-your-own-hardware.md) and
  [cap what they spend](../outcomes/cap-agent-spending.md): the two guides this demo rests on.
- [The greeter live demo](../greeter-live-demo.md): a longer run that uses paid engines.

## Say it in one line

A small non-profit can have AI agents build a volunteer sign-up page on its own computer, at no per-token cost, and hand its board a record of every decision.

## Improve this demo

If a command here printed something different, or a link does not prove its sentence, that is a
good first contribution, and a recorded run of this walk-through would be a better one. This
page is
[`docs/guides/demos/non-profit.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/demos/non-profit.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying which step and what you saw.
