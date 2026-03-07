-- =============================================================================
-- 003_cleanup_stale_model_pricing.sql
-- Remove the old bare model ID inserted before PR #30 corrected it to
-- the cross-region inference profile prefix (us.anthropic.claude-sonnet-4-6).
-- =============================================================================

DELETE FROM model_pricing
WHERE model_id = 'anthropic.claude-sonnet-4-6';
