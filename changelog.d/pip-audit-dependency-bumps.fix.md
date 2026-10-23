* **`pip-audit` is green again:** `pypdf` 6.19.0→6.21.2 (eight advisories), `black` 26.5.1→26.10.1
  and the OpenTelemetry family 1.44.0→1.45.1 (`opentelemetry-api`/`-sdk`, the 0.66b1
  instrumentation packages and `azure-monitor-opentelemetry` 1.8.11), which have to move
  together. `Gate 7 - pip-audit` was failing on `develop` itself, which held every pull request
  in the repair state.
