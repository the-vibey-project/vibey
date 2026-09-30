-- A checkout is held by at most one LIVE project; an abandoned one lets it go.
--
-- 0001 made `repo_path` unique across every project, so that two live projects never
-- share a checkout. It also meant a project that was abandoned held its checkout for
-- ever: nothing could start in that path again, and `vibey new` on it failed with a raw
-- unique violation (live on #963, 2026-09-30, after `vibey abandon` of 893c4fc1).
--
-- The rule is narrowed to what it was for. `abandoned` is terminal -- the phase machine
-- gives it no way out (`domain/phase.py`, `_EDGES[Phase.ABANDONED]` is
-- empty) -- so an abandoned row can never become live again and collide. Every other
-- phase, `done` included, still holds its checkout. The literal is `Phase.ABANDONED`'s
-- value, and the ORM declares the same predicate (`orm_models.py`, `ProjectOrm`).
--
-- Forward-only and safe on any existing data: the new index is strictly weaker than the
-- one it replaces, so no row that satisfied 0001 can violate it. A plain partial unique
-- index, which PostgreSQL 14 supports (no `NULLS NOT DISTINCT`, no 15+ syntax).
DROP INDEX project_repo_uniq;
CREATE UNIQUE INDEX project_repo_live_uniq ON project (repo_path) WHERE phase <> 'abandoned';
