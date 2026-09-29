-- Durable GitHub triage order (ADR-0054 / sub-doctrine 10.g).
-- GitHub remains the source of issue content and labels; this table is the local,
-- transactional ordering and lease authority used before a Vibey project exists.
CREATE TYPE triaged_ticket_state AS ENUM ('ready', 'leased', 'dispatched', 'blocked', 'completed');

CREATE SEQUENCE triaged_ticket_bump_seq AS bigint;

CREATE TABLE triaged_ticket (
    repository       text NOT NULL,
    issue_number     integer NOT NULL CHECK (issue_number > 0),
    title            text NOT NULL,
    body             text NOT NULL DEFAULT '',
    issue_url        text NOT NULL,
    priority_rank    integer NOT NULL CHECK (priority_rank BETWEEN 0 AND 3),
    bump_seq         bigint,
    state            triaged_ticket_state NOT NULL DEFAULT 'ready',
    project_id       uuid REFERENCES project(id) ON DELETE SET NULL,
    lease_owner      text,
    lease_expires_at timestamptz,
    source_updated_at timestamptz,
    observed_at      timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (repository, issue_number),
    CONSTRAINT triaged_ticket_bump_positive CHECK (bump_seq IS NULL OR bump_seq > 0),
    CONSTRAINT triaged_ticket_lease_consistent CHECK (
        (state = 'leased') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)
    )
);

CREATE INDEX triaged_ticket_claim ON triaged_ticket (
    (bump_seq IS NULL), bump_seq ASC NULLS LAST, priority_rank ASC,
    source_updated_at ASC NULLS LAST, issue_number ASC
) WHERE state = 'ready';

CREATE INDEX triaged_ticket_expiring ON triaged_ticket (lease_expires_at)
    WHERE state = 'leased';
