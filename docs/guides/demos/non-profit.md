---
description: A walk-through for a small non-profit team that builds a volunteer shift sign-up tool on a local model with a spending brake, answers the questions only people can, and ends with a record a board can read.
---

# The non-profit demo: a volunteer sign-up tool, a budget you set, a machine you own

This is the second audience vibey names, after open-source developers
([ADR-0087](../../architecture/decisions/0087-the-six-audiences-in-order.md)). It follows
one small, invented project, a page where volunteers pick a shift, from an empty machine
to a finished build and a record you can hand to someone else. The organisation is
illustrative: nothing here describes a real team, adopter or result.

**What vibey is, in one breath.** An AI coding agent writes software from plain-English
requests. vibey is the program that manages those agents like a project manager: it asks
you questions first, builds without you, checks the work, and writes every step to a
record that can only be added to.

**Why this suits a small team with little money.** The agents can run on a computer you
own, so there is no per-token bill; a cap stops spending if you ever allow a paid agent;
and the questions that are yours (what the tool should do, whether the result is good
enough) wait for you instead of being guessed.

## Before you start: the honest costs

- **A strong enough computer.** The local model needs a Mac with 24 GB of memory or more,
  or a graphics card with about 16 GB (recommended, not yet verified); a 16 GB Mac cannot run it
  ([hardware](../../reference/system-requirements.md#hardware)). If your team has no such
  machine, this demo is not yet for you, and that is a real gap.
- **About 14 GB to download once**, and about 20 GB of disk.
- **Someone comfortable in a terminal.** You type the commands below. vibey does not
  replace that person; it spares them the babysitting.
- **Software that is free but not costless.** The licence is MIT and local turns are
  priced at zero in the ledger. Electricity, the machine and your volunteers' time are not.

## 1. Set it up once

Install vibey, PostgreSQL and Ollama, and pull the model. The steps are the first three of
[run agents on your own hardware](../outcomes/run-agents-on-your-own-hardware.md#steps);
follow them and keep the two database roles they describe, because the record's
protection depends on it.

```bash
vibey doctor --sovereign-fit    # measures whether the model fits this machine
```

## 2. Start the project with a brake on it

```bash
vibey new shift-signup --repo ~/src/shift-signup --max-cycle-dollars 15 --max-cycle-turns 200
```

The cap is a backstop. The first line of defence is the allow-list in step 4, which keeps
paid agents out altogether. The cap only matters if someone later allows one, and then it
parks the work and asks before spending more
([cap what agents spend](../outcomes/cap-agent-spending.md)).

## 3. Give the interview your own words

The local model cannot browse the web. It reads notes you give it, and with none it stops
and asks rather than invent a source. Put your volunteer handbook, a list of shifts and
anything about who may see volunteers' details into a folder; start each file with a
`source:` line.

```bash
export VIBEY_EVIDENCE_DIR=~/notes/shift-signup
vibey doctor --engine gptossloop --conformance --record
```

The second command records that the local engine passed its checks; vibey uses no engine
until that has happened.

## 4. Build on the local model only

```bash
vibey worker --provider gptossloop --engines gptossloop
vibey gates        # in a second terminal: what is waiting for you
```

`vibey gates` prints each question with the exact `vibey answer` command that answers it.
These are your decisions: what the page must do, what it must never show. When the
interview is finished, you accept the design yourself:

```bash
vibey design accept PROJECT_ID --no-visual
```

Building then runs without you. You can stop the worker at any time: work lives in a queue
and the database, and a restarted worker picks up where the last one stopped.

## 5. Review it, and stop short of deploying

When the build is done, vibey parks two questions for you in turn: your verdict on the
result, then whether to deploy at all.

```bash
vibey answer GATE_ID --verdict accept
vibey answer GATE_ID --choice local_only
```

`local_only` is a complete finish. This demo stops here on purpose, because the
deployment stages are not yet proven against real cloud accounts
([deploy without holding cloud secrets](../outcomes/deploy-without-storing-secrets.md)).

## 6. Hand someone the record

```bash
vibey cost                                       # spend this cycle, per engine
vibey ledger show --limit 100                    # every decision and answer, in order
vibey ledger export PROJECT_ID -o ledger.jsonl   # a shard with its hash-chain head
```

On the all-local path `vibey cost` shows zero for every engine. The export writes the
chain head into the file, and you copy the file off the machine so the head cannot be
rewritten by whoever can rewrite the database
([keep a tamper-evident record](../outcomes/keep-a-tamper-evident-record.md#steps)).
What the shard leaves out, and why, is in [what gets published](../ledger-publication.md).

## The evidence

| Claim | Where it is proved |
|---|---|
| The default engine is local and runs on your hardware | [ADR-0064](../../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md) |
| `--engines` confines the worker, and local engines are chosen first | [ADR-0038](../../architecture/decisions/0038-local-engines-are-preferred-first.md) |
| A tripped cap parks a gate instead of spending | [ADR-0024](../../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md) |
| No internet is needed at runtime on this path | [Network](../../reference/system-requirements.md#network) |
| The ledger refuses edits and is exported with a chain head | [ADR-0055](../../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md) |
| Deployment needs your recorded consent | [ADR-0014](../../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md) |

## Limits

- **This walk-through has not been recorded end to end.** Each command was checked
  against `vibey --help` for that command on 2026-10-07, at `develop` commit `56f226a62`,
  and each step's claims come from the guides linked above. A single unbroken run on one
  machine is not on record, so the demo describes what you will see and shows no output
  it did not capture.
- **The reviewer is the builder.** With one local engine, the check of each finished item
  is done by the engine that wrote it, and vibey records that weaker independence
  ([ADR-0035](../../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
  Have a person read what matters.
- **A local model is not a frontier model.** [The honest ceiling](../local-models-ollama.md#the-honest-ceiling)
  says what it can carry; expect to answer more questions and fix more by hand.
- **Your volunteers' data is yours to protect.** vibey keeps its own traffic on your
  machine. The app it builds, its hosting and what it stores are your responsibility, and
  vibey makes no claim about any privacy or charity law.
- **A funder may not accept the record.** vibey supplies a record and checks, not an
  audit. Whether a board, funder or regulator is satisfied is theirs to say, and the
  export has no verify command yet.
- **No grant, service or support comes with this.** It is a free tool and a guide.

## Go deeper

- [Run agents on your own hardware](../outcomes/run-agents-on-your-own-hardware.md) and
  [cap what they spend](../outcomes/cap-agent-spending.md): the two guides this demo rests on.
- [The greeter live demo](../greeter-live-demo.md): a longer run that uses paid engines.

## Improve this demo

If a command here printed something different, or a link does not prove its sentence, that
is a good first contribution, and a recorded run of this walk-through would be a better
one. This page is
[`docs/guides/demos/non-profit.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/demos/non-profit.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying which step and what you saw.
