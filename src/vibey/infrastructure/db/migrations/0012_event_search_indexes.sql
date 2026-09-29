-- Indexes for `vibey ledger search` (sub-doctrine 7.a, the searchable ledger; #137).
-- Each serves one search dimension that 0002's indexes could not:
--   --digest            a digest names a payload, so it is looked up across events
--   --since / --until   a project's events by production instant
--   --actor ENGINE      a project's events by engine, newest first by seq
-- Record id is the primary key; kind is event_kind (0002). Free text has no index:
-- payload::text ILIKE cannot use the jsonb_path_ops GIN index, which answers
-- containment, not substrings.
CREATE INDEX event_digest              ON event (digest);
CREATE INDEX event_project_produced_at ON event (project_id, produced_at);
CREATE INDEX event_project_engine      ON event (project_id, engine_id, seq);
