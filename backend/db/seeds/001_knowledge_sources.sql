-- =============================================================================
-- 001_knowledge_sources.sql
-- Seed all 13 playbooks from Connors-EO/solution-accelerator
-- Idempotent: ON CONFLICT (id) DO NOTHING
-- =============================================================================

INSERT INTO knowledge_sources (id, source_type, source_ref, domain_tags, phase_relevance, retrieval_strategy, retrieval_config, tenant_id)
VALUES

-- -------------------------------------------------------------------------
-- Existing playbooks (playbooks/existing/)
-- -------------------------------------------------------------------------
(
  'IAC-001',
  'github_file',
  'playbooks/existing/iac-terraform-multi-account.md',
  ARRAY['infrastructure-as-code', 'terraform'],
  ARRAY['P0', 'P1', 'P2', 'P3', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/existing/iac-terraform-multi-account.md"}'::jsonb,
  'everops'
),
(
  'IAC-002',
  'github_file',
  'playbooks/existing/iac-atmos-foundations.md',
  ARRAY['infrastructure-as-code', 'terraform', 'atmos'],
  ARRAY['P0', 'P1', 'P2', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/existing/iac-atmos-foundations.md"}'::jsonb,
  'everops'
),
(
  'K8S-001',
  'github_file',
  'playbooks/existing/k8s-cluster-deployment-hardening.md',
  ARRAY['kubernetes', 'containers'],
  ARRAY['P0', 'P1', 'P2', 'P3', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/existing/k8s-cluster-deployment-hardening.md"}'::jsonb,
  'everops'
),
(
  'ZTNA-001',
  'github_file',
  'playbooks/existing/ztna-sso-integration.md',
  ARRAY['identity', 'zero-trust', 'security'],
  ARRAY['P0', 'P1', 'P2', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/existing/ztna-sso-integration.md"}'::jsonb,
  'everops'
),
(
  'CICD-001',
  'github_file',
  'playbooks/existing/cicd-pipeline-standardization.md',
  ARRAY['cicd', 'devops'],
  ARRAY['P0', 'P1', 'P2', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/existing/cicd-pipeline-standardization.md"}'::jsonb,
  'everops'
),

-- -------------------------------------------------------------------------
-- Wave-1 playbooks (playbooks/wave-1/)
-- -------------------------------------------------------------------------
(
  'CLOUD-001',
  'github_file',
  'playbooks/wave-1/cloud-platform-architecture-landing-zone.md',
  ARRAY['cloud-infrastructure', 'landing-zone'],
  ARRAY['P0', 'P1', 'P2', 'P3', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/cloud-platform-architecture-landing-zone.md"}'::jsonb,
  'everops'
),
(
  'CLOUD-003',
  'github_file',
  'playbooks/wave-1/cloud-migration-modernization.md',
  ARRAY['cloud-infrastructure', 'cloud-migration'],
  ARRAY['P0', 'P1', 'P2', 'P3', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/cloud-migration-modernization.md"}'::jsonb,
  'everops'
),
(
  'OBS-001',
  'github_file',
  'playbooks/wave-1/observability-platform-implementation.md',
  ARRAY['observability'],
  ARRAY['P0', 'P1', 'P2', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/observability-platform-implementation.md"}'::jsonb,
  'everops'
),
(
  'SEC-001',
  'github_file',
  'playbooks/wave-1/security-maturity-assessment-roadmap.md',
  ARRAY['security'],
  ARRAY['P0', 'P1', 'P2', 'P3', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/security-maturity-assessment-roadmap.md"}'::jsonb,
  'everops'
),
(
  'SEC-002',
  'github_file',
  'playbooks/wave-1/cloud-security-posture-cnapp.md',
  ARRAY['security', 'cloud-infrastructure'],
  ARRAY['P0', 'P1', 'P2', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/cloud-security-posture-cnapp.md"}'::jsonb,
  'everops'
),
(
  'FINOPS-001',
  'github_file',
  'playbooks/wave-1/finops-foundation-cost-optimization.md',
  ARRAY['finops'],
  ARRAY['P0', 'P1', 'P2', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/finops-foundation-cost-optimization.md"}'::jsonb,
  'everops'
),
(
  'NET-001',
  'github_file',
  'playbooks/wave-1/cloud-network-architecture.md',
  ARRAY['networking'],
  ARRAY['P0', 'P1', 'P2', 'P3', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/cloud-network-architecture.md"}'::jsonb,
  'everops'
),
(
  'NET-002',
  'github_file',
  'playbooks/wave-1/hybrid-multi-cloud-connectivity.md',
  ARRAY['networking', 'hybrid-cloud'],
  ARRAY['P0', 'P1', 'P2', 'P5'],
  'cag',
  '{"repo_owner":"Connors-EO","repo_name":"solution-accelerator","branch":"main","path":"playbooks/wave-1/hybrid-multi-cloud-connectivity.md"}'::jsonb,
  'everops'
)

ON CONFLICT (id) DO NOTHING;
