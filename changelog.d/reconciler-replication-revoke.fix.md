* **db:** the role reconciler no longer silently leaves `session_replication_role` grantable.
  The grant lives in `pg_parameter_acl`, one row for the whole cluster, so two reconciles on
  different databases of one cluster race on it (a per-database advisory lock cannot
  serialize them), and the loser's `REVOKE` fails with `tuple concurrently updated`. Every
  `PostgresError` there was swallowed, so the trigger-silencing grant stayed in place without
  a word (CI, PostgreSQL 16, 2026-10-01). Now only a lack of privilege is tolerated (the
  inspector reports it, as documented); a concurrent update is retried with a short backoff,
  up to five attempts; anything else is raised.
