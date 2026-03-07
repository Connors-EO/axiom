-- =============================================================================
-- engagement.sql
-- Shared test fixture for Epic 3 turn pipeline tests.
-- Loaded inside a transaction that is rolled back after each test.
-- Requires: app.tenant_id = 'test'
-- =============================================================================

-- Test engagement
INSERT INTO engagements (
    id,
    tenant_id,
    model_id,
    current_phase,
    domain_tags,
    phase_context,
    flags
) VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'test',
    'us.anthropic.claude-sonnet-4-6',
    'RESEARCH_DISCOVERY',
    ARRAY['cloud-platform'],
    '{}'::jsonb,
    '{}'::jsonb
);

-- Three messages for that engagement (so turn_number = 4 in tests)
INSERT INTO messages (id, role, content, phase, engagement_id, tenant_id, turn_number)
VALUES
  ('b0000000-0000-0000-0000-000000000001', 'user',      'What is the current cloud setup?',    'RESEARCH_DISCOVERY', 'a0000000-0000-0000-0000-000000000001', 'test', 1),
  ('b0000000-0000-0000-0000-000000000002', 'assistant', 'Let me investigate the cloud setup.', 'RESEARCH_DISCOVERY', 'a0000000-0000-0000-0000-000000000001', 'test', 2),
  ('b0000000-0000-0000-0000-000000000003', 'user',      'Can you be more specific?',           'RESEARCH_DISCOVERY', 'a0000000-0000-0000-0000-000000000001', 'test', 3);

-- Two knowledge_sources matching domain_tag 'cloud-platform' and phase 'RESEARCH_DISCOVERY'
INSERT INTO knowledge_sources (id, source_type, source_ref, domain_tags, phase_relevance, retrieval_strategy, retrieval_config, tenant_id)
VALUES
  (
    'cloud-001',
    'github_file',
    'playbooks/wave-1/cloud-platform-architecture-landing-zone.md',
    ARRAY['cloud-platform'],
    ARRAY['RESEARCH_DISCOVERY', 'INTAKE'],
    'cag',
    '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/cloud-platform-architecture-landing-zone.md"}'::jsonb,
    'test'
  ),
  (
    'cloud-002',
    'github_file',
    'playbooks/wave-1/cloud-migration-modernization.md',
    ARRAY['cloud-platform', 'cloud-migration'],
    ARRAY['RESEARCH_DISCOVERY', 'INTAKE'],
    'cag',
    '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/cloud-migration-modernization.md"}'::jsonb,
    'test'
  );

-- Model pricing for the test model (model_pricing uses open_read RLS policy)
INSERT INTO model_pricing (model_id, display_name, input_cost_per_1k, output_cost_per_1k, cache_write_per_1k, cache_read_per_1k, thinking_per_1k, context_window, updated_at)
VALUES (
    'us.anthropic.claude-sonnet-4-6',
    'Claude Sonnet (cross-region)',
    0.003000,
    0.015000,
    0.003750,
    0.000300,
    NULL,
    200000,
    NOW()
)
ON CONFLICT (model_id) DO NOTHING;
