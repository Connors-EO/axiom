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
