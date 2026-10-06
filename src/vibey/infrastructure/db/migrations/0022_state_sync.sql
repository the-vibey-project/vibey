-- The state sync's watermark (ADR-0086): for each state branch, the commit this database
-- last agreed with, the base of the next three-way merge. Never synced itself: it says
-- where this database stands, which no other database shares. It moves only after what
-- it marks is committed here (sub-doctrine 10.g).
CREATE TABLE state_sync (
    remote       text PRIMARY KEY,
    base_commit  text NOT NULL CHECK (base_commit ~ '^[0-9a-f]{40}([0-9a-f]{24})?$'),
    synced_at    timestamptz NOT NULL DEFAULT now()
);
