---
description: Look inside a vibey project's ledger in your browser, block-explorer style. Search every public decision, question, finding and phase change, read it in plain words, check its digest yourself, and see exactly what was left out.
---

# Ledger explorer

A block explorer for software work. Every vibey project keeps an append-only ledger of
what happened to it; this page opens the public part of one, for anyone, with no account.

<div id="ledger-explorer-app" data-base="data/" data-guide="../guides/ledger-publication/">
  <noscript>
    <p>The explorer needs JavaScript. The same records are plain JSON under
    <code>explorer/data/&lt;project&gt;/</code>: <code>manifest.json</code>,
    <code>index.json</code> and <code>records/&lt;event id&gt;.json</code>.</p>
  </noscript>
</div>

## How to use it

- **Search** with the box at the top: a word (`cancel`), a sequence number (`#12`), an event
  id, or a digest. A search for one exact record opens it directly. Press <kbd>/</kbd> from
  anywhere to jump to the box.
- **Narrow** with the kind chips (decisions, findings, questions and so on) and the phase strip
  (design, build, review). Every view has its own link, so you can send someone to exactly
  what you are looking at.
- **Open a record** to read what it says in plain words, then check it. Use <kbd>←</kbd> and
  <kbd>→</kbd> to walk the ledger one record at a time.

## What you can trust, and why

- **Each record can be checked by you.** Your browser recomputes the record's SHA-256 digest
  from the payload on screen and says whether it matches. Nothing here asks you to take the
  page's word for it.
- **The gaps are counted, not hidden.** The bar on the first screen shows how much of the
  ledger is public and how much was withheld, and why. The chain head covers every event,
  withheld ones included, so anyone holding the full ledger can confirm this is a true slice.
- **Nothing is sent anywhere.** The page reads static files; what you search for stays in
  your browser.

[What gets published](../guides/ledger-publication.md) lists every rule the publication policy
applies, and what it removes.

## Publish a ledger here

The explorer reads what `vibey ledger site` writes, so a project appears here by publishing its
shard and building the site beside the documentation:

```bash
vibey ledger export <project-id> --out ledger/<name>.jsonl
vibey ledger site --from ledger/<name>.jsonl --out docs/explorer/data/<name> --json-only
```

Then add the project to `docs/explorer/data/projects.json`. Publishing is a decision: the
export is a *projection* (default-deny, with local paths and email addresses taken out), but
the answers you typed during design are published as you typed them, so read the shard before
you commit it.

Until a project does, the page shows a clearly marked **sample**, built by
`scripts/explorer_sample.py` through the same exporter and policy. It describes no real project.
