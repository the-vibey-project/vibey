* **`vibey-gh doctor` no longer reports a false error on this repository's own configuration:** it called
  `[version] regenerate` (and the two legacy `[documentation]` names the loader still accepts) keys vibey-gh ignores.
  Its key list is now checked against the keys the loader reads, and doctor is run over every configuration the
  repository ships, so the list cannot drift again unnoticed.
