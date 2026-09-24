-- Queue priority's lane is derived (ADR-0054 item 6): exactly the jobs bumped (or enqueued
-- prioritised) BY NAME and not since un-bumped, plus all their unfinished transitive
-- dependencies. 0014 recorded where each bumped job came from (bump_origin); the derived
-- rule needs only whether a job is in the named set, so this adds that flag.
--
-- EXPAND, not contract. A worker still running the 0014 release reads `bump_origin` from
-- every `SELECT *` and `RETURNING *` its row mapper maps, so the column stays, unused by
-- this release. It is dropped by a later contract migration, 0016_drop_job_bump_origin,
-- once no worker older than this release is running. Only 0014's CHECK tying it to
-- bump_seq goes now, because this release no longer writes it.
--
-- No lane membership changes here. The rule 0014 shipped with could leave a pulled job in
-- the lane with nothing named needing it; clearing it is a correction, and corrections are
-- ledger events that only vibey's writer can build faithfully (the digest and the delivery
-- correlation id are computed there). The project's next reorder request sweeps such a job
-- out of the lane and records it (JobPriority* `removed`).
ALTER TABLE job ADD COLUMN bump_named boolean NOT NULL DEFAULT false;
UPDATE job SET bump_named = true WHERE bump_seq IS NOT NULL AND bump_origin = id;

ALTER TABLE job DROP CONSTRAINT job_bump_origin_with_seq;
ALTER TABLE job ADD CONSTRAINT job_bump_named_in_lane
    CHECK (NOT bump_named OR bump_seq IS NOT NULL);
