-- The ledger guard's functions pin their search_path (review of #1100, ADR-0055).
--
-- Migration 0016 created `ledger_refuse_rewrite()` and `ledger_guard_partitions()`
-- with the caller's search_path, and the owner runs the second on every migration run.
-- A role that may CREATE in `public` -- every role, on PostgreSQL 14 and on any
-- database upgraded from it -- could plant an operator or function there that an
-- unqualified name inside them resolves to, and have it run as the owner. The review
-- did exactly that through the reconcile's own catalog query and wiped the ledger.
--
-- Both functions are replaced with bodies that name every object by schema and run
-- with `search_path = pg_catalog, pg_temp`, so nothing outside pg_catalog can be
-- resolved in their place. 0016 is not edited: it has shipped.

CREATE OR REPLACE FUNCTION public.ledger_refuse_rewrite() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION 'the ledger is append-only: % on % is refused', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege',
              HINT = 'Corrections are new events that supersede prior ones '
                     '(CLAUDE.md non-negotiable; ADR-0055).';
END $$;

CREATE OR REPLACE FUNCTION public.ledger_guard_partitions() RETURNS integer
LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    part  regclass;
    added integer := 0;
BEGIN
    FOR part IN
        SELECT t.relid FROM pg_catalog.pg_partition_tree('public.event'::pg_catalog.regclass) t
        WHERE t.relid OPERATOR(pg_catalog.<>) 'public.event'::pg_catalog.regclass
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_catalog.pg_trigger g
            WHERE g.tgrelid OPERATOR(pg_catalog.=) part
              AND g.tgname OPERATOR(pg_catalog.=) 'event_no_truncate'
        ) THEN
            -- With this search_path a regclass prints schema-qualified.
            EXECUTE pg_catalog.format(
                'CREATE TRIGGER event_no_truncate BEFORE TRUNCATE ON %s '
                'FOR EACH STATEMENT EXECUTE FUNCTION public.ledger_refuse_rewrite()',
                part
            );
            added := added + 1;
        END IF;
    END LOOP;
    RETURN added;
END $$;

REVOKE EXECUTE ON FUNCTION public.ledger_guard_partitions() FROM PUBLIC;
