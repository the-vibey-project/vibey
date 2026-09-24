-- The ledger is append-only by the database, not by convention (ADR-0055).
--
-- CLAUDE.md's non-negotiable: "The ledger is append-only. No updates, no deletes.
-- Corrections are new events that supersede prior ones." Migrations 0002 and 0013
-- enforced it with `DO INSTEAD NOTHING` rules on the partitioned parent, which bind
-- only a query addressed to `event` itself: an UPDATE or DELETE addressed to a
-- partition changed rows, TRUNCATE emptied the ledger (rules never fire on it), and
-- the table's owner could disable or drop the rules. The rules also made a stray
-- write a silent no-op, which hides the attempt instead of refusing it.
--
-- Triggers replace them. They refuse loudly, a row trigger on a partitioned table is
-- cloned onto every partition that exists now and every one attached later, and the
-- statement-level TRUNCATE guard (which Postgres does not clone) is attached to each
-- partition by `ledger_guard_partitions()`, run here and after every migration run.
-- The owner can still disable a trigger; the boundary against that is the role the
-- application connects as, which neither owns the ledger nor holds UPDATE, DELETE or
-- TRUNCATE on it (infrastructure/db/ledger_guard.py).

CREATE OR REPLACE FUNCTION ledger_refuse_rewrite() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'the ledger is append-only: % on % is refused', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege',
              HINT = 'Corrections are new events that supersede prior ones '
                     '(CLAUDE.md non-negotiable; ADR-0055).';
END $$;

DROP RULE IF EXISTS event_no_update ON event;
DROP RULE IF EXISTS event_no_delete ON event;

CREATE TRIGGER event_append_only
    BEFORE UPDATE OR DELETE ON event
    FOR EACH ROW EXECUTE FUNCTION ledger_refuse_rewrite();

CREATE TRIGGER event_no_truncate
    BEFORE TRUNCATE ON event
    FOR EACH STATEMENT EXECUTE FUNCTION ledger_refuse_rewrite();

-- Attaches the TRUNCATE guard to every partition of `event`, at any depth, that lacks
-- it, and returns how many it attached. Idempotent.
CREATE OR REPLACE FUNCTION ledger_guard_partitions() RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
    part  regclass;
    added integer := 0;
BEGIN
    FOR part IN
        SELECT relid FROM pg_partition_tree('event'::regclass) WHERE relid <> 'event'::regclass
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger WHERE tgrelid = part AND tgname = 'event_no_truncate'
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER event_no_truncate BEFORE TRUNCATE ON %s '
                'FOR EACH STATEMENT EXECUTE FUNCTION ledger_refuse_rewrite()',
                part
            );
            added := added + 1;
        END IF;
    END LOOP;
    RETURN added;
END $$;

REVOKE EXECUTE ON FUNCTION ledger_guard_partitions() FROM PUBLIC;

SELECT ledger_guard_partitions();
