-- ACP sessions and their logs, kept by the hub for the principal that created them (SP-ACP).
--
-- `vibey acp` runs where no database credential is (ADR-0055, ADR-0100), so it keeps each
-- session through the hub, which writes these two tables. Both are append-only, as the ledger
-- is: a mode change, a project attach and a close are new rows, never an edit. The same
-- `public.ledger_refuse_rewrite()` the ledger uses (migrations 0016, 0017) refuses an UPDATE,
-- a DELETE or a TRUNCATE loudly, and the application role is granted only SELECT and INSERT
-- on them (infrastructure/db/ledger_guard.py).

CREATE TABLE acp_session (
    session_id  text PRIMARY KEY,
    cwd         text NOT NULL,
    created_by  text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- `session/list`: one principal's sessions, optionally under one folder.
CREATE INDEX acp_session_created_by ON acp_session (created_by, cwd);

CREATE TABLE acp_session_event (
    session_id   text NOT NULL REFERENCES acp_session,
    seq          bigint NOT NULL CHECK (seq >= 1),
    kind         text NOT NULL CHECK (kind IN (
                     'user_message', 'agent_message', 'tool_call', 'tool_call_update',
                     'plan', 'mode', 'attach', 'title', 'closed'
                 )),
    payload      jsonb NOT NULL,
    recorded_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, seq)
);

-- A session's newest event of one kind (its mode, project, title) in one probe, so neither a
-- list page nor a load reads a log from its start.
CREATE INDEX acp_session_event_kind ON acp_session_event (session_id, kind, seq);

CREATE TRIGGER acp_session_append_only
    BEFORE UPDATE OR DELETE ON acp_session
    FOR EACH ROW EXECUTE FUNCTION public.ledger_refuse_rewrite();

CREATE TRIGGER acp_session_no_truncate
    BEFORE TRUNCATE ON acp_session
    FOR EACH STATEMENT EXECUTE FUNCTION public.ledger_refuse_rewrite();

CREATE TRIGGER acp_session_event_append_only
    BEFORE UPDATE OR DELETE ON acp_session_event
    FOR EACH ROW EXECUTE FUNCTION public.ledger_refuse_rewrite();

CREATE TRIGGER acp_session_event_no_truncate
    BEFORE TRUNCATE ON acp_session_event
    FOR EACH STATEMENT EXECUTE FUNCTION public.ledger_refuse_rewrite();
