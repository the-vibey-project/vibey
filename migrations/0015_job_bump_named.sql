-- Queue priority's lane is derived (ADR-0054 item 6): exactly the jobs bumped (or enqueued
-- prioritised) BY NAME and not since un-bumped, plus all their unfinished transitive
-- dependencies. 0014 recorded where each bumped job came from (bump_origin); the derived
-- rule needs only whether a job is in the named set, so the column becomes a flag.
--
-- The rule 0014 shipped with could leave a pulled job in the lane with nothing named
-- needing it (bump a and b that share a dependency, then un-bump both). Such orphans are
-- cleared here, so the lane this migration leaves behind is already its derivation.
ALTER TABLE job ADD COLUMN bump_named boolean NOT NULL DEFAULT false;
UPDATE job SET bump_named = true WHERE bump_seq IS NOT NULL AND bump_origin = id;

ALTER TABLE job DROP CONSTRAINT job_bump_origin_with_seq;
ALTER TABLE job DROP COLUMN bump_origin;
ALTER TABLE job ADD CONSTRAINT job_bump_named_in_lane
    CHECK (NOT bump_named OR bump_seq IS NOT NULL);

WITH RECURSIVE lane(id) AS (
    SELECT id FROM job
    WHERE bump_named AND state NOT IN ('succeeded', 'failed', 'cancelled')
  UNION
    SELECT d.depends_on_job_id
    FROM lane l
    JOIN job_dependency d ON d.job_id = l.id
    JOIN job p ON p.id = d.depends_on_job_id
    WHERE p.state NOT IN ('succeeded', 'failed', 'cancelled')
)
UPDATE job SET bump_seq = NULL, bump_named = false
WHERE bump_seq IS NOT NULL
  AND state NOT IN ('succeeded', 'failed', 'cancelled')
  AND id NOT IN (SELECT id FROM lane);
