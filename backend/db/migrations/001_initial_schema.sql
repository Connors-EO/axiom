-- =============================================================================
-- 001_initial_schema.sql
-- Axiom complete database schema — Solution Architecture v2.2 / Data Observability Guide v1.1
-- =============================================================================

-- Migration tracking (bootstrap — also referenced by migrate.ts before first run)
CREATE TABLE IF NOT EXISTS schema_migrations (
  id         SERIAL       PRIMARY KEY,
  filename   TEXT         NOT NULL UNIQUE,
  applied_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- engagements
-- =============================================================================
CREATE TABLE IF NOT EXISTS engagements (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  current_phase TEXT         NOT NULL DEFAULT 'P0',
  domain_tags   TEXT[]       NOT NULL DEFAULT '{}',
  phase_context JSONB,
  flags         JSONB,
  model_id      TEXT,
  tenant_id     TEXT         NOT NULL,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE engagements ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagements FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON engagements
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_engagements_tenant_id ON engagements (tenant_id);
CREATE INDEX idx_engagements_model_id   ON engagements (model_id);
CREATE INDEX idx_engagements_created_at ON engagements (created_at);

-- =============================================================================
-- messages
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
  id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  role                TEXT         NOT NULL,
  content             TEXT         NOT NULL,
  phase               TEXT         NOT NULL,
  data_classification TEXT,
  engagement_id       UUID         NOT NULL REFERENCES engagements (id),
  tenant_id           TEXT         NOT NULL,
  turn_number         INTEGER      NOT NULL,
  created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON messages
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_messages_engagement_id ON messages (engagement_id);
CREATE INDEX idx_messages_tenant_id     ON messages (tenant_id);
CREATE INDEX idx_messages_created_at    ON messages (created_at);

-- =============================================================================
-- traces  (Data Observability Guide v1.1)
-- =============================================================================
CREATE TABLE IF NOT EXISTS traces (
  id                            UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  engagement_id                 UUID          REFERENCES engagements (id),
  model_id                      TEXT,
  tenant_id                     TEXT          NOT NULL,
  phase                         TEXT,
  input_tokens                  INTEGER,
  output_tokens                 INTEGER,
  estimated_cost_usd            DECIMAL(12,6),
  expected_structured_output    BOOLEAN       NOT NULL,          -- v1.1 addition
  retrieval_events              JSONB,
  playbooks_selected            TEXT[],
  uncertainty_flag_count        INTEGER,
  structured_output_compliance  BOOLEAN,
  latency_ms                    INTEGER,
  created_at                    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

ALTER TABLE traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE traces FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON traces
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_traces_engagement_id ON traces (engagement_id);
CREATE INDEX idx_traces_tenant_id     ON traces (tenant_id);
CREATE INDEX idx_traces_model_id      ON traces (model_id);
CREATE INDEX idx_traces_created_at    ON traces (created_at);

-- =============================================================================
-- quality_snapshots
-- =============================================================================
CREATE TABLE IF NOT EXISTS quality_snapshots (
  id                                UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_date                     DATE          NOT NULL,
  model_id                          TEXT,
  phase                             TEXT,
  tenant_id                         TEXT          NOT NULL,
  total_traces                      INTEGER,
  structured_output_compliance_rate DECIMAL(5,4),
  avg_latency_ms                    DECIMAL(10,2),
  avg_cost_usd                      DECIMAL(12,6),
  created_at                        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

ALTER TABLE quality_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_snapshots FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON quality_snapshots
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_quality_snapshots_tenant_id  ON quality_snapshots (tenant_id);
CREATE INDEX idx_quality_snapshots_model_id   ON quality_snapshots (model_id);
CREATE INDEX idx_quality_snapshots_created_at ON quality_snapshots (created_at);

-- =============================================================================
-- gate_decisions  (immutable — no UPDATE/DELETE intended)
-- =============================================================================
CREATE TABLE IF NOT EXISTS gate_decisions (
  id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  phase              TEXT         NOT NULL,
  status             TEXT         NOT NULL CHECK (status IN ('PASS', 'WARN', 'FAIL')),
  approved_by        TEXT,
  criteria_evaluated JSONB,
  tenant_id          TEXT         NOT NULL,
  created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE gate_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE gate_decisions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON gate_decisions
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_gate_decisions_tenant_id  ON gate_decisions (tenant_id);
CREATE INDEX idx_gate_decisions_created_at ON gate_decisions (created_at);

-- =============================================================================
-- phase_transitions
-- =============================================================================
CREATE TABLE IF NOT EXISTS phase_transitions (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  from_phase    TEXT         NOT NULL,
  to_phase      TEXT         NOT NULL,
  reason        TEXT,
  triggered_by  TEXT,
  engagement_id UUID         NOT NULL REFERENCES engagements (id),
  tenant_id     TEXT         NOT NULL,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE phase_transitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE phase_transitions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON phase_transitions
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_phase_transitions_engagement_id ON phase_transitions (engagement_id);
CREATE INDEX idx_phase_transitions_tenant_id     ON phase_transitions (tenant_id);
CREATE INDEX idx_phase_transitions_created_at    ON phase_transitions (created_at);

-- =============================================================================
-- knowledge_sources
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_sources (
  id                 TEXT         PRIMARY KEY,
  source_type        TEXT         NOT NULL,
  source_ref         TEXT,
  domain_tags        TEXT[]       NOT NULL DEFAULT '{}',
  phase_relevance    TEXT[]       NOT NULL DEFAULT '{}',
  retrieval_strategy TEXT         NOT NULL CHECK (retrieval_strategy IN ('cag', 'rag')),
  retrieval_config   JSONB,
  preferred_model    TEXT,
  tenant_id          TEXT         NOT NULL DEFAULT 'everops',
  created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_sources FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON knowledge_sources
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_knowledge_sources_tenant_id  ON knowledge_sources (tenant_id);
CREATE INDEX idx_knowledge_sources_created_at ON knowledge_sources (created_at);

-- =============================================================================
-- knowledge_cache
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_cache (
  id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id      TEXT         NOT NULL REFERENCES knowledge_sources (id),
  processed_text TEXT,
  is_stale       BOOLEAN      NOT NULL DEFAULT false,
  expires_at     TIMESTAMPTZ,
  content_hash   TEXT,
  tenant_id      TEXT         NOT NULL,
  created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE knowledge_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_cache FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON knowledge_cache
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_knowledge_cache_tenant_id  ON knowledge_cache (tenant_id);
CREATE INDEX idx_knowledge_cache_created_at ON knowledge_cache (created_at);

-- =============================================================================
-- artifacts
-- =============================================================================
CREATE TABLE IF NOT EXISTS artifacts (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  state         TEXT         NOT NULL CHECK (state IN ('DRAFT', 'REVISED', 'APPROVED')),
  engagement_id UUID         NOT NULL REFERENCES engagements (id),
  content       TEXT,
  tenant_id     TEXT         NOT NULL,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON artifacts
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_artifacts_engagement_id ON artifacts (engagement_id);
CREATE INDEX idx_artifacts_tenant_id     ON artifacts (tenant_id);
CREATE INDEX idx_artifacts_created_at    ON artifacts (created_at);

-- =============================================================================
-- lessons
-- =============================================================================
CREATE TABLE IF NOT EXISTS lessons (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  content       TEXT         NOT NULL,
  domain_tags   TEXT[]       NOT NULL DEFAULT '{}',
  engagement_id UUID         REFERENCES engagements (id), -- nullable after generalization
  tenant_id     TEXT         NOT NULL,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE lessons FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON lessons
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_lessons_engagement_id ON lessons (engagement_id);
CREATE INDEX idx_lessons_tenant_id     ON lessons (tenant_id);
CREATE INDEX idx_lessons_created_at    ON lessons (created_at);

-- =============================================================================
-- model_pricing  (global — no tenant_id; open RLS policy)
-- =============================================================================
CREATE TABLE IF NOT EXISTS model_pricing (
  model_id           TEXT          PRIMARY KEY,
  display_name       TEXT          NOT NULL,
  input_cost_per_1k  DECIMAL(10,6) NOT NULL,
  output_cost_per_1k DECIMAL(10,6) NOT NULL,
  cache_write_per_1k DECIMAL(10,6),
  cache_read_per_1k  DECIMAL(10,6),
  thinking_per_1k    DECIMAL(10,6) NULL,
  context_window     INTEGER       NOT NULL,
  updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

ALTER TABLE model_pricing ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_pricing FORCE ROW LEVEL SECURITY;

-- Pricing is global/shared; all tenants can read
CREATE POLICY open_read ON model_pricing USING (true);

-- =============================================================================
-- finetuning_runs
-- =============================================================================
CREATE TABLE IF NOT EXISTS finetuning_runs (
  run_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  model_base       TEXT         NOT NULL,
  split_date       DATE         NOT NULL,
  training_turn_ids UUID[]      NOT NULL DEFAULT '{}',
  holdout_turn_ids  UUID[]      NOT NULL DEFAULT '{}',
  status           TEXT         NOT NULL DEFAULT 'pending',
  erasure_flag     BOOLEAN      NOT NULL DEFAULT false,
  tenant_id        TEXT         NOT NULL,
  created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

ALTER TABLE finetuning_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE finetuning_runs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON finetuning_runs
  USING (tenant_id = current_setting('app.tenant_id', true));

CREATE INDEX idx_finetuning_runs_tenant_id  ON finetuning_runs (tenant_id);
CREATE INDEX idx_finetuning_runs_created_at ON finetuning_runs (created_at);
