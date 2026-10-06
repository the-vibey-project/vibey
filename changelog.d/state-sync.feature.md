* **cli:** `vibey state sync` keeps this database and a sealed copy of it on the
  repository's `vibey-state` branch the same, in both directions. The merge is three-way
  against the commit last synced, with a declared conflict rule per table, and the ledger
  is never resolved by a rule. The copy is encrypted with AES-256-GCM, and the branch moves
  only by compare-and-swap. A second sync straight after a first writes nothing.
  `vibey state status`, `export`, `import`, `forget` and `key` go with it, configured by
  `VIBEY_STATE_*`. `[supervisor] state_sync = true` keeps it running with its own
  environment file. With a `VIBEY_STATE_KEY` secret and no declared database, `vibey -w`
  restores the state before the command and syncs the run's changes back. The hub never
  offers it (ADR-0086).
* **ci:** any GitHub workflow can open the synced state with the composite action
  `.github/actions/vibey-state` (`open`, then `close`), and write it back through the
  reusable `.github/workflows/vibey-state-write.yml`, whose one job alone holds
  `contents: write`. A private repository may always; a public one only when
  `.github/vibey-state.toml` declares `[state] public = true`, because whatever a workflow
  prints from the decrypted state is then public. This repository declares it (ADR-0086).
