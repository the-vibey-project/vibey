* **The krypton app takes the patched `decode-uri-component`, which clears the advisory gate:** GHSA-qr28-fpjm-wq7f
  (high, a denial of service through quadratic replacement of percent-encoded runs) affects every release up to 0.5.0,
  and the only dependent, `query-string@7` under `expo-router`, pins `^0.2.2`, so the lockfile could not move. An npm
  `overrides` entry takes 0.5.1 (ESM-only; Metro and Jest load it, and the web export builds). Retire the override when
  `expo-router` moves off `query-string@7`.
