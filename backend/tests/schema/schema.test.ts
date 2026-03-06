import { pool } from '../../src/db/client';
import { tableExists, columnExists, getColumnInfo, rlsEnabled } from './helpers';

const ALL_TABLES = [
  'engagements',
  'messages',
  'traces',
  'quality_snapshots',
  'gate_decisions',
  'phase_transitions',
  'knowledge_sources',
  'knowledge_cache',
  'artifacts',
  'lessons',
  'model_pricing',
  'finetuning_runs',
];

afterAll(async () => {
  await pool.end();
});

describe('Schema: all 12 tables exist', () => {
  it.each(ALL_TABLES)('table %s exists', async (tableName) => {
    expect(await tableExists(tableName)).toBe(true);
  });
});

describe('Schema: RLS enabled on all 12 tables', () => {
  it.each(ALL_TABLES)('RLS enabled on %s', async (tableName) => {
    expect(await rlsEnabled(tableName)).toBe(true);
  });
});

describe('Schema: traces table structure', () => {
  it('has expected_structured_output column of type boolean and NOT NULL', async () => {
    const col = await getColumnInfo('traces', 'expected_structured_output');
    expect(col).not.toBeNull();
    expect(col?.data_type).toBe('boolean');
    expect(col?.is_nullable).toBe('NO');
  });
});

describe('Schema: model_pricing table structure', () => {
  it('has thinking_per_1k column that is nullable', async () => {
    const col = await getColumnInfo('model_pricing', 'thinking_per_1k');
    expect(col).not.toBeNull();
    expect(col?.is_nullable).toBe('YES');
  });
});

describe('Schema: finetuning_runs table structure', () => {
  it('has training_turn_ids column', async () => {
    expect(await columnExists('finetuning_runs', 'training_turn_ids')).toBe(true);
  });

  it('has holdout_turn_ids column', async () => {
    expect(await columnExists('finetuning_runs', 'holdout_turn_ids')).toBe(true);
  });
});

describe('Schema: NOT NULL constraints', () => {
  it('rejects null tenant_id on engagements', async () => {
    await expect(
      pool.query(
        `INSERT INTO engagements (id, tenant_id, current_phase)
         VALUES (gen_random_uuid(), NULL, 'P0')`
      )
    ).rejects.toThrow();
  });
});

describe('Schema: RLS cross-tenant isolation', () => {
  it('hides rows from other tenants', async () => {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      await client.query("SET LOCAL app.tenant_id = 'test_rls_tenant_a'");
      await client.query(
        `INSERT INTO engagements (id, tenant_id, current_phase)
         VALUES (gen_random_uuid(), 'test_rls_tenant_a', 'P0')`
      );
      await client.query("SET LOCAL app.tenant_id = 'test_rls_tenant_b'");
      const result = await client.query(
        `SELECT count(*)::int AS cnt FROM engagements
         WHERE tenant_id = 'test_rls_tenant_a'`
      );
      expect(result.rows[0].cnt).toBe(0);
      await client.query('ROLLBACK');
    } finally {
      client.release();
    }
  });
});

describe('Schema: FK constraints', () => {
  it('rejects message with nonexistent engagement_id', async () => {
    await expect(
      pool.query(
        `INSERT INTO messages (id, engagement_id, tenant_id, role, content, phase, turn_number)
         VALUES (
           gen_random_uuid(),
           '00000000-0000-0000-0000-000000000000',
           'tenant_a',
           'user',
           'hello',
           'P0',
           1
         )`
      )
    ).rejects.toThrow();
  });
});

describe('Schema: schema_migrations tracking', () => {
  it('schema_migrations table exists', async () => {
    expect(await tableExists('schema_migrations')).toBe(true);
  });

  it('has at least one applied migration recorded', async () => {
    const result = await pool.query(
      `SELECT filename FROM schema_migrations ORDER BY applied_at`
    );
    expect(result.rows.length).toBeGreaterThan(0);
    expect(result.rows[0].filename as string).toContain('001_initial_schema');
  });
});
