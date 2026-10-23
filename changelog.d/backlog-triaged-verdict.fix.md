* **The backlog loop comments once on a newly triaged issue:** an entry the loop records for an issue it just
  triaged (no probes yet) used to evaluate as `OPEN` while its stored verdict was `NEEDS-TRIAGE`, so the
  idempotency guard missed and each such issue was commented on a second time. It now keeps `NEEDS-TRIAGE`
  until probes are added.
