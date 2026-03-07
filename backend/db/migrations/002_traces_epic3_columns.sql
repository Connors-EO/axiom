-- =============================================================================
-- 002_traces_epic3_columns.sql
-- Add Epic 3 columns to traces table for full turn pipeline observability
-- =============================================================================

ALTER TABLE traces
  ADD COLUMN IF NOT EXISTS session_id        UUID,
  ADD COLUMN IF NOT EXISTS turn_number       INTEGER,
  ADD COLUMN IF NOT EXISTS model_provider    TEXT,
  ADD COLUMN IF NOT EXISTS model_latency_ms  INTEGER,
  ADD COLUMN IF NOT EXISTS total_latency_ms  INTEGER,
  ADD COLUMN IF NOT EXISTS intent_classified TEXT,
  ADD COLUMN IF NOT EXISTS scope_check       TEXT,
  ADD COLUMN IF NOT EXISTS playbooks_failed  TEXT[];
