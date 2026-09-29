-- Ledger partitioning (vibey#114).
--
-- 0003_ledger_partitioning.sql used to live below the migrator's discovered root and
-- only created an unused shadow table. This migration is deliberately self-contained:
-- it preserves every row, swaps the live table, recreates the append-only protections
-- and indexes, and verifies the copy before removing the legacy table.

ALTER INDEX IF EXISTS event_project_seq RENAME TO event_legacy_project_seq_0013;
ALTER INDEX IF EXISTS event_kind RENAME TO event_legacy_kind_0013;
ALTER INDEX IF EXISTS event_correlation RENAME TO event_legacy_correlation_0013;
ALTER INDEX IF EXISTS event_payload_gin RENAME TO event_legacy_payload_gin_0013;
ALTER INDEX IF EXISTS event_digest RENAME TO event_legacy_digest_0013;
ALTER INDEX IF EXISTS event_project_produced_at RENAME TO event_legacy_produced_at_0013;
ALTER INDEX IF EXISTS event_project_engine RENAME TO event_legacy_engine_0013;
ALTER INDEX IF EXISTS event_seq_uniq RENAME TO event_legacy_seq_uniq_0013;
ALTER TABLE event RENAME TO event_legacy_0013;

CREATE TABLE event_partitioned_0013 (
    event_id        uuid NOT NULL DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    seq             bigint NOT NULL,
    cycle           integer NOT NULL,
    phase           phase NOT NULL,
    kind            text NOT NULL,
    engine_id       text,
    job_id          uuid,
    causation_id    uuid,
    correlation_id  uuid NOT NULL,
    provenance      provenance NOT NULL DEFAULT 'agent',
    produced_at     timestamptz NOT NULL DEFAULT now(),
    payload         jsonb NOT NULL,
    digest          text NOT NULL,
    CONSTRAINT event_seq_uniq PRIMARY KEY (project_id, seq),
    CONSTRAINT event_id_seq_uniq UNIQUE (event_id, seq)
) PARTITION BY RANGE (seq);

-- The default partition is intentional. It makes the first deployment lossless for
-- every existing and future sequence; operators can add bounded range partitions later
-- without changing the application table name or moving rows by hand.
CREATE TABLE event_partitioned_0013_default
    PARTITION OF event_partitioned_0013 DEFAULT;

INSERT INTO event_partitioned_0013 (
    event_id, project_id, seq, cycle, phase, kind, engine_id, job_id,
    causation_id, correlation_id, provenance, produced_at, payload, digest
)
SELECT
    event_id, project_id, seq, cycle, phase, kind, engine_id, job_id,
    causation_id, correlation_id, provenance, produced_at, payload, digest
FROM event_legacy_0013
ORDER BY project_id, seq;

ALTER TABLE event_partitioned_0013 RENAME TO event;

CREATE INDEX event_project_seq   ON event (project_id, seq);
CREATE INDEX event_kind          ON event (project_id, kind, seq);
CREATE INDEX event_correlation   ON event (correlation_id, seq);
CREATE INDEX event_payload_gin   ON event USING gin (payload jsonb_path_ops);
CREATE INDEX event_digest              ON event (digest);
CREATE INDEX event_project_produced_at ON event (project_id, produced_at);
CREATE INDEX event_project_engine      ON event (project_id, engine_id, seq);

-- Append-only: no UPDATE, no DELETE. The protection is attached to the live parent,
-- so it remains in force when bounded child partitions are added later.
CREATE RULE event_no_update AS ON UPDATE TO event DO INSTEAD NOTHING;
CREATE RULE event_no_delete AS ON DELETE TO event DO INSTEAD NOTHING;

DO $$
DECLARE
    old_count bigint;
    new_count bigint;
BEGIN
    SELECT count(*) INTO old_count FROM event_legacy_0013;
    SELECT count(*) INTO new_count FROM event;
    IF old_count <> new_count THEN
        RAISE EXCEPTION 'ledger partition copy lost rows: old %, new %', old_count, new_count;
    END IF;
END $$;

DROP TABLE event_legacy_0013;

-- Rebind the function body to the new live relation after the table swap. The sequence
-- remains unchanged, so the next number and all existing project cursors are preserved.
CREATE OR REPLACE FUNCTION append_event(
    p_project_id     uuid,
    p_cycle          integer,
    p_phase          phase,
    p_kind           text,
    p_engine_id      text,
    p_job_id         uuid,
    p_causation_id   uuid,
    p_correlation_id uuid,
    p_provenance     provenance,
    p_payload        jsonb,
    p_digest         text
) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE s bigint;
BEGIN
    INSERT INTO event_seq (project_id, next_seq)
    VALUES (p_project_id, 2)
    ON CONFLICT (project_id) DO UPDATE SET next_seq = event_seq.next_seq + 1
    RETURNING next_seq - 1 INTO s;

    INSERT INTO event (
        project_id, seq, cycle, phase, kind, engine_id, job_id,
        causation_id, correlation_id, provenance, payload, digest
    ) VALUES (
        p_project_id, s, p_cycle, p_phase, p_kind, p_engine_id, p_job_id,
        p_causation_id, p_correlation_id, p_provenance, p_payload, p_digest
    );

    RETURN s;
END $$;
