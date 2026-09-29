-- The hub's live feed (ADR-0067): every ledger append announces itself on the channel
-- `vibey_ledger_appended`, with the project and the new event's seq as its payload.
--
-- Additive: one trigger function and one AFTER INSERT trigger on the partitioned `event`
-- table (PostgreSQL clones it onto every partition, present and future). It writes
-- nothing; the append-only guard (0016, 0017) is untouched. NOTIFY is delivered only when
-- the appending transaction commits, so a listener never hears of an event it cannot read.
--
-- The payload is a position, never a timestamp (sub-doctrine 10.g): a listener reads
-- every event after the last seq it delivered, so a notification that is lost -- the
-- listener was reconnecting, the queue overflowed -- costs latency, never an event.
-- Like 0017's functions, this one names everything by schema and pins its search_path.

CREATE OR REPLACE FUNCTION public.ledger_announce_append() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    PERFORM pg_catalog.pg_notify(
        'vibey_ledger_appended',
        pg_catalog.json_build_object('project_id', NEW.project_id, 'seq', NEW.seq)::text
    );
    RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS event_announce_append ON public.event;
CREATE TRIGGER event_announce_append
    AFTER INSERT ON public.event
    FOR EACH ROW EXECUTE FUNCTION public.ledger_announce_append();
