-- Ledger Partitioning Migration (vibey#114)
-- We use declarative partitioning by RANGE on the `seq` column.

-- 1. Create the partitioned table
CREATE TABLE event_partitioned (
    event_id UUID NOT NULL,
    project_id UUID NOT NULL,
    cycle INT NOT NULL,
    phase TEXT NOT NULL,
    seq INT NOT NULL,
    kind TEXT NOT NULL,
    engine_id TEXT,
    job_id UUID,
    causation_id UUID,
    correlation_id UUID NOT NULL,
    provenance TEXT NOT NULL,
    produced_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    digest TEXT NOT NULL,
    PRIMARY KEY (project_id, seq)
) PARTITION BY RANGE (seq);

-- 2. Migration logic (to be run by a python script)
-- Move data from event to event_partitioned
-- INSERT INTO event_partitioned SELECT * FROM event;

-- 3. Rename tables
-- ALTER TABLE event RENAME TO event_old;
-- ALTER TABLE event_partitioned RENAME TO event;

-- 4. Create initial partitions (e.g., every 1M events)
-- CREATE TABLE event_p1 PARTITION OF event FOR VALUES FROM (0) TO (1000000);
-- CREATE TABLE event_p2 PARTITION OF event FOR VALUES FROM (1000000) TO (2000000);
