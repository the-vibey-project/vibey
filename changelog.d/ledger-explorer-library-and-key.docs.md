* **docs:** the ledger explorer now lists every project's public, scrubbed ledger (`scripts/explorer_publish.py`,
  configured by `scripts/explorer_publish.toml`) with a searchable project library as its front door, and the
  state key opens the withheld remainder in place: the sealed copy `vibey state sync` keeps on the `vibey-state`
  branch is downloaded, decrypted in the browser and its hash chain recomputed there. Floats are hashed as
  Python wrote them, so records with decimal numbers verify.
