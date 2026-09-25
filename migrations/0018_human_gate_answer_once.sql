-- A gate is answered once (vibey Lane D, `fix/gate-answer-cas`). An answer is written by a
-- compare-and-set on `answered_at IS NULL`, so a replayed or duplicate answer can no longer
-- overwrite the first. Each answer records the id of the request that made it, so the same
-- request replayed is recognised as a no-op rather than refused as a second answer.
--
-- Additive: gates answered before this migration keep a NULL request id, which matches no
-- request, so any later answer to them is refused as it should be.
ALTER TABLE human_gate ADD COLUMN answer_request_id text;
ALTER TABLE human_gate ADD CONSTRAINT human_gate_request_id_with_answer
    CHECK (answer_request_id IS NULL OR answered_at IS NOT NULL);
