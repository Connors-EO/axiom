import { pool } from '../../src/db/client';

export async function tableExists(tableName: string): Promise<boolean> {
  const result = await pool.query(
    `SELECT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = $1
    ) AS exists`,
    [tableName]
  );
  return result.rows[0].exists as boolean;
}

export async function columnExists(
  tableName: string,
  columnName: string
): Promise<boolean> {
  const result = await pool.query(
    `SELECT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2
    ) AS exists`,
    [tableName, columnName]
  );
  return result.rows[0].exists as boolean;
}

export async function getColumnInfo(
  tableName: string,
  columnName: string
): Promise<{ data_type: string; is_nullable: string } | null> {
  const result = await pool.query(
    `SELECT data_type, is_nullable
     FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2`,
    [tableName, columnName]
  );
  return (result.rows[0] as { data_type: string; is_nullable: string }) ?? null;
}

export async function rlsEnabled(tableName: string): Promise<boolean> {
  const result = await pool.query(
    `SELECT relrowsecurity FROM pg_class
     WHERE relname = $1 AND relnamespace = 'public'::regnamespace`,
    [tableName]
  );
  return result.rows[0]?.relrowsecurity === true;
}

export async function queryAsTenant<T extends object>(
  sql: string,
  tenant: string,
  params?: unknown[]
): Promise<T[]> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query(`SET LOCAL app.tenant_id = '${tenant}'`);
    const result = await client.query(sql, params ?? []);
    await client.query('COMMIT');
    return result.rows as T[];
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}
