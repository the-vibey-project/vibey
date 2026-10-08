* **ledger:** `vibey ledger site` no longer rejects a shard whose records name an engine, phase, kind or
  provenance this release has no member for (e.g. `agyloop`, retired by ADR-0078). The value is kept whole and
  written back unchanged, as vibey#287 already requires of every other reader of those columns.
