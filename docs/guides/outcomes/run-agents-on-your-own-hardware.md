---
description: Run vibey on its default engine, GPT-OSS 20B on Ollama, and allow only that engine; the queue, the ledger and the model then stay on one machine, and the measured sovereign path needs no internet at runtime.
---

# How do I run AI coding agents entirely on my own hardware?

**Short answer:** run vibey on its default engine, GPT-OSS 20B on Ollama, and allow only
that engine; the queue, the ledger and the model then stay on one machine, and the measured
sovereign path needs no internet at runtime.

Most AI coding agents send your code to a vendor's model. That is a problem when the code
is not yours to send, when the network is not there, or when you would rather not pay per
token. vibey's default engine, `gptossloop`, is a local one: it runs GPT-OSS 20B through
[Ollama](https://ollama.com) on the machine vibey runs on
([ADR-0064](../../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)).
This page takes you from an empty machine to a worker that can reach no model but that one.

## Check the machine first

Memory decides whether this works. The figures below come from one machine, re-measured
every week, and some are derived from those measurements; the
[system requirements](../../reference/system-requirements.md#hardware) page has the full
table and says which is which.

- **Apple Silicon:** 24 GB of unified memory is the minimum and 32 GB is recommended. A
  16 GB Mac cannot run it: DESIGN alone needs more than 16 GiB (a derived verdict, not
  measured on 16 GB hardware).
- **A discrete GPU:** 12,339 to 12,974 MiB of GPU memory for `gpt-oss:20b`; a 16 GB card
  is the recommendation, not yet verified on CUDA.
- **CPU only:** enough for the design interview, not for building. A worst-case BUILD
  turn takes longer than vibey's 900-second request timeout.
- **Disk and download:** about 20 GB free, and about 14 GB to download once, almost all of
  it the model.

## Steps

**1. Install vibey and PostgreSQL.** Follow [Install](../../index.md#install): install
`vibey-engine`, let `vibey install --postgres` set up the database, and run `vibey migrate`
with the owner's connection string. Keep two database roles, as that section shows; the
ledger's guard depends on it.

**2. Install Ollama and pull the model.** The [local models guide](../local-models-ollama.md)
has the server settings sized for agent work. The short form:

```bash
ollama pull gpt-oss:20b
export VIBEY_OLLAMA_URL=http://127.0.0.1:11434   # the one local endpoint setting
vibey doctor --sovereign-fit                      # measures whether the model fits this machine
```

**3. Create a project and give the design interview something to read.** The local model
has no web access. Its research step reads files you put in `VIBEY_EVIDENCE_DIR`, each
starting with a `source:` line, and with none it stops and asks rather than invent a source
([`[design.research]`](../../reference/configuration.md#designresearch)).

```bash
vibey new my-app --repo ~/src/my-app
export VIBEY_EVIDENCE_DIR=~/notes/my-app          # reading for the research step
vibey doctor --engine gptossloop --conformance --record
```

The last line matters: a worker selects no engine until a recorded conformance run has
passed for it ([`vibey doctor`](../../reference/cli.md#vibey-doctor)).

**4. Start a worker that can use only the local engine.**

```bash
vibey worker --provider gptossloop --engines gptossloop
```

`--provider gptossloop` keeps the design interview and the work plan on the local model;
`--engines gptossloop` is an allow-list, so no paid engine can be selected for building
([`vibey worker`](../../reference/cli.md#vibey-worker)). Answer the questions it parks
with `vibey gates` and `vibey answer`, as in the [Quickstart](../../index.md#quickstart).

**5. Confirm it.** `vibey engines` lists the engines this project has recorded, and
`vibey cost` shows the spend: every local engine is priced at zero
([local models guide](../local-models-ollama.md)).

## What stays on the machine, and what needs the internet

At runtime the sovereign path talks to three local ports and nothing else, as measured by a
network pass on 2026-09-29 ([host allowlist](../../reference/system-requirements.md#host-allowlist)):
PostgreSQL on 5432, Ollama on 11434, and the hub on 8765 when a krypton app connects. No
telemetry, analytics, update check or version check is made at runtime
([network](../../reference/system-requirements.md#network)); vibey's metrics recorder has
no external exporter ([`[telemetry]`](../../reference/configuration.md#telemetry)).

With every outbound connection cut, the everyday commands still worked in the same pass:
`new`, `work` on the local provider, `answer`, `worker --once`, `status`, `gates`, `cost`,
`budget`, `serve` and more ([offline capability](../../reference/system-requirements.md#offline-capability)).
What needs the internet is installing packages, pulling models, the paid engines, webhooks,
the GitHub bridge, the Azure deployment stages and the Kubernetes operator.

## The evidence

| Claim | Where it is proved |
|---|---|
| The default engine is local and on without a switch | [ADR-0064](../../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md) |
| Local engines are chosen before paid ones | [ADR-0038](../../architecture/decisions/0038-local-engines-are-preferred-first.md); [`preferred_tier` in `rotation.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/rotation.py) |
| `--engines` confines the worker to its list | [`vibey worker`](../../reference/cli.md#vibey-worker); ADR-0038, point 5 |
| No internet at runtime on the sovereign path | [Network table](../../reference/system-requirements.md#network), generated from [`minimum-specs.json`](https://github.com/the-vibey-project/vibey/blob/develop/docs/architecture/evidence/minimum-specs.json) |
| Research never invents a source | [ADR-0027](../../architecture/decisions/0027-sovereign-design-provider.md) |

## Limits

- **One engine reviews its own work.** With `gptossloop` alone, the check of each finished
  item is done by the engine that wrote it, and vibey records that weakened independence
  in the ledger ([ADR-0035](../../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
  The strict setting that refuses a self-review, `verify.require_independent_review`, is
  read from the stored project record, which neither `vibey new` nor the operator writes
  it into today ([what is read at runtime](../../reference/configuration.md#what-is-read-at-runtime-today)).
  The dependable fix is a second local engine: switching on `qwenloop`
  (`VIBEY_FEATURE_QWENLOOP=1`, `--engines gptossloop,qwenloop`) gives each item a
  different local reviewer, at the price of a second model and its memory.
- **A local model is not a frontier model.** [The honest ceiling](../local-models-ollama.md#the-honest-ceiling)
  says what GPT-OSS 20B can and cannot carry today.
- **One machine was measured.** Every measured figure comes from an Apple M5 with 24 GiB;
  other hardware is derived or [not verified](../../reference/system-requirements.md#not-verified).
- **Your project's own commands are yours.** The allowlist covers vibey. The build and test
  commands in your repository run as they always do, network and all.
- **The paid engines' libraries still install.** They ship in the base package, so a
  sovereign-only install downloads them too; they are never called unless allowed.

## Go deeper

- [Local models on Ollama](../local-models-ollama.md): the full recipe, a second local
  engine, and capacity fits.
- [The sovereign driver and local fit](../../paper.md#the-sovereign-driver-and-local-fit),
  in the research paper.

## Improve this guide

If a step failed on your machine, or a link here does not prove what the sentence says,
that is a good first contribution. This page is
[`docs/guides/outcomes/run-agents-on-your-own-hardware.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/run-agents-on-your-own-hardware.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying which step and what you saw.
