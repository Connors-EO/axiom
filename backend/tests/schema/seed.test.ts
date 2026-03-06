import { pool } from '../../src/db/client';
import { runSeeds } from '../../src/db/seed';
import { queryAsTenant } from './helpers';

beforeAll(async () => {
  await runSeeds();
});

afterAll(async () => {
  await pool.end();
});

describe('Seed: knowledge_sources row count', () => {
  it('has exactly 13 rows', async () => {
    const rows = await queryAsTenant<{ cnt: number }>(
      'SELECT count(*)::int AS cnt FROM knowledge_sources',
      'everops'
    );
    expect(rows[0].cnt).toBe(13);
  });
});

describe('Seed: knowledge_sources domain_tags', () => {
  it('every row has non-empty domain_tags', async () => {
    const rows = await queryAsTenant<{ domain_tags: string[] }>(
      'SELECT domain_tags FROM knowledge_sources',
      'everops'
    );
    expect(rows.length).toBe(13);
    for (const row of rows) {
      expect(row.domain_tags.length).toBeGreaterThan(0);
    }
  });
});

describe('Seed: knowledge_sources phase_relevance', () => {
  it('every row has non-empty phase_relevance', async () => {
    const rows = await queryAsTenant<{ phase_relevance: string[] }>(
      'SELECT phase_relevance FROM knowledge_sources',
      'everops'
    );
    expect(rows.length).toBe(13);
    for (const row of rows) {
      expect(row.phase_relevance.length).toBeGreaterThan(0);
    }
  });
});

describe('Seed: knowledge_sources retrieval_strategy', () => {
  it('every row has retrieval_strategy = cag', async () => {
    const rows = await queryAsTenant<{ retrieval_strategy: string }>(
      'SELECT retrieval_strategy FROM knowledge_sources',
      'everops'
    );
    expect(rows.length).toBe(13);
    for (const row of rows) {
      expect(row.retrieval_strategy).toBe('cag');
    }
  });
});

describe('Seed: knowledge_sources retrieval_config', () => {
  it('every row has retrieval_config with all required keys', async () => {
    const rows = await queryAsTenant<{ retrieval_config: Record<string, string> }>(
      'SELECT retrieval_config FROM knowledge_sources',
      'everops'
    );
    expect(rows.length).toBe(13);
    for (const row of rows) {
      expect(row.retrieval_config).toHaveProperty('repo_owner');
      expect(row.retrieval_config).toHaveProperty('repo_name');
      expect(row.retrieval_config).toHaveProperty('branch');
      expect(row.retrieval_config).toHaveProperty('path');
    }
  });
});

describe('Seed: model_pricing', () => {
  it('has exactly 2 rows', async () => {
    const result = await pool.query(
      'SELECT count(*)::int AS cnt FROM model_pricing'
    );
    expect(result.rows[0].cnt).toBe(2);
  });

  it('both rows have input_cost_per_1k > 0', async () => {
    const result = await pool.query(
      'SELECT input_cost_per_1k FROM model_pricing'
    );
    expect(result.rows.length).toBe(2);
    for (const row of result.rows as { input_cost_per_1k: string }[]) {
      expect(parseFloat(row.input_cost_per_1k)).toBeGreaterThan(0);
    }
  });
});

describe('Seed: idempotency', () => {
  it('running seed twice gives same row counts', async () => {
    await runSeeds();
    const ksRows = await queryAsTenant<{ cnt: number }>(
      'SELECT count(*)::int AS cnt FROM knowledge_sources',
      'everops'
    );
    const mpResult = await pool.query(
      'SELECT count(*)::int AS cnt FROM model_pricing'
    );
    expect(ksRows[0].cnt).toBe(13);
    expect(mpResult.rows[0].cnt).toBe(2);
  });
});
