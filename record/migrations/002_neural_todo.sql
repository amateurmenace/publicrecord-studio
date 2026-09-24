-- The segments still waiting for a meaning vector, findable without a
-- table scan. The desk counts them per town every time it opens, the
-- backfill selects them a hundred at a time, and the HNSW index cannot
-- answer "which rows are NULL" (it ignores them). Partial on purpose: it
-- shrinks to nothing as the backlog drains (specs/27; measured 2026-09-24).
CREATE INDEX IF NOT EXISTS idx_seg_neural_todo
    ON segments (town, meeting_id) WHERE emb_neural IS NULL;
