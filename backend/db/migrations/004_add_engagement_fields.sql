-- =============================================================================
-- 004_add_engagement_fields.sql
-- Add title, client_name, and engagement_type to engagements table.
-- These fields were deferred from Epic 3 and are required by the
-- axiom-engagement Lambda handler (Story 4.6).
-- =============================================================================

ALTER TABLE engagements
  ADD COLUMN IF NOT EXISTS title           TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS client_name     TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS engagement_type TEXT NOT NULL DEFAULT '';
