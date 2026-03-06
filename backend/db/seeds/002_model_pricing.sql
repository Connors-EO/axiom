-- =============================================================================
-- 002_model_pricing.sql
-- Seed model pricing for Claude Sonnet and Amazon Nova Pro
-- Idempotent: ON CONFLICT (model_id) DO UPDATE SET updated_at = NOW()
-- =============================================================================
-- IMPORTANT: VERIFY ALL COSTS AGAINST CURRENT BEDROCK PRICING BEFORE PRODUCTION

INSERT INTO model_pricing (
  model_id,
  display_name,
  input_cost_per_1k,   -- VERIFY AGAINST CURRENT BEDROCK PRICING BEFORE PRODUCTION
  output_cost_per_1k,  -- VERIFY AGAINST CURRENT BEDROCK PRICING BEFORE PRODUCTION
  cache_write_per_1k,  -- VERIFY AGAINST CURRENT BEDROCK PRICING BEFORE PRODUCTION
  cache_read_per_1k,   -- VERIFY AGAINST CURRENT BEDROCK PRICING BEFORE PRODUCTION
  thinking_per_1k,     -- VERIFY AGAINST CURRENT BEDROCK PRICING BEFORE PRODUCTION
  context_window,
  updated_at
)
VALUES

-- Claude Sonnet — primary reasoning model
(
  'anthropic.claude-sonnet-4-6',
  'Claude Sonnet',
  0.003000,   -- $3.00 per 1M input tokens (placeholder)
  0.015000,   -- $15.00 per 1M output tokens (placeholder)
  0.003750,   -- $3.75 per 1M cache write tokens (placeholder)
  0.000300,   -- $0.30 per 1M cache read tokens (placeholder)
  NULL,       -- thinking_per_1k not applicable for this model
  200000,
  NOW()
),

-- Amazon Nova Pro — cost-efficient alternative model
(
  'amazon.nova-pro-v1:0',
  'Amazon Nova Pro',
  0.000810,   -- ~0.27x Claude Sonnet input rate (placeholder)
  0.003150,   -- ~0.21x Claude Sonnet output rate (placeholder)
  0.001013,   -- placeholder
  0.000081,   -- placeholder
  0.001000,   -- thinking_per_1k (placeholder)
  300000,
  NOW()
)

ON CONFLICT (model_id) DO UPDATE SET updated_at = NOW();
