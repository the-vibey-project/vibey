-- Queue priority (ADR-0054): a bump puts a job ahead of all un-bumped waiting work,
-- behind every job bumped before it.
--
-- bump_seq is the job's place among bumped jobs: NULL for a job in normal order, else a
-- number drawn from job_bump_seq at the moment of the bump. A sequence, not a timestamp:
-- one bump moves a job and its dependencies in one transaction, where now() is the same
-- instant for all of them, and first-in-first-out among bumped jobs needs a strict
-- order that a clock cannot give (sub-doctrine 10.g: a timestamp is not a position).
--
-- bump_origin is the job whose bump moved this one: itself when it was bumped by name,
-- the named job when it was pulled forward as a dependency. An un-bump reads it to undo
-- exactly what a bump moved. Set and cleared together with bump_seq.
--
-- The claim orders bump_seq ASC NULLS LAST ahead of what it ordered by before, so the
-- order among un-bumped jobs is exactly what it was. The columns are queue state; the
-- history of every request is the JobPriority* events on the append-only ledger,
-- written in the same transaction.
CREATE SEQUENCE job_bump_seq AS bigint;

ALTER TABLE job ADD COLUMN bump_seq bigint;
ALTER TABLE job ADD COLUMN bump_origin uuid;

-- Added NOT VALID, then validated: the constraint is taken without holding the table
-- lock through a full scan, and the scan that follows only needs a lighter one.
ALTER TABLE job ADD CONSTRAINT job_bump_seq_positive
    CHECK (bump_seq IS NULL OR bump_seq > 0) NOT VALID;
ALTER TABLE job VALIDATE CONSTRAINT job_bump_seq_positive;
ALTER TABLE job ADD CONSTRAINT job_bump_origin_with_seq
    CHECK ((bump_seq IS NULL) = (bump_origin IS NULL)) NOT VALID;
ALTER TABLE job VALIDATE CONSTRAINT job_bump_origin_with_seq;

-- A worker still running the previous release claims by the old index order and ignores
-- bump_seq until it is replaced: during a rolling upgrade a bump is honoured by the new
-- workers only (ADR-0054, Consequences).
DROP INDEX job_claim;
CREATE INDEX job_claim
    ON job (project_id, bump_seq ASC NULLS LAST, priority DESC, run_after ASC, id ASC)
    WHERE state = 'ready';
