-- Queue priority (ADR-0054): a bump puts a job ahead of all un-bumped waiting work,
-- behind every job bumped before it.
--
-- bump_seq is the job's place among bumped jobs: NULL for a job in normal order, else a
-- number drawn from job_bump_seq at the moment of the bump. A sequence, not a timestamp:
-- one bump moves a job and its dependencies in one transaction, where now() is the same
-- instant for all of them, and first-in-first-out among bumped jobs needs a strict
-- order that a clock cannot give (sub-doctrine 10.g: a timestamp is not a position).
--
-- The claim orders bump_seq ASC NULLS LAST ahead of what it ordered by before, so the
-- order among un-bumped jobs is exactly what it was. The column is queue state; the
-- history of every bump and un-bump is the JobPriorityBumped / JobPriorityUnbumped
-- events on the append-only ledger, written in the same transaction.
CREATE SEQUENCE job_bump_seq AS bigint;

ALTER TABLE job ADD COLUMN bump_seq bigint;
ALTER TABLE job ADD CONSTRAINT job_bump_seq_positive CHECK (bump_seq IS NULL OR bump_seq > 0);

DROP INDEX job_claim;
CREATE INDEX job_claim
    ON job (project_id, bump_seq ASC NULLS LAST, priority DESC, run_after ASC, id ASC)
    WHERE state = 'ready';
