import * as fs from 'fs';
import * as path from 'path';
import { pool } from './client';

export async function runSeeds(): Promise<void> {
  const seedsDir = path.join(__dirname, '../../db/seeds');
  const files = fs
    .readdirSync(seedsDir)
    .filter((f) => f.endsWith('.sql'))
    .sort();

  const client = await pool.connect();
  try {
    await client.query("SET app.tenant_id = 'everops'");
    for (const file of files) {
      const sql = fs.readFileSync(path.join(seedsDir, file), 'utf8');
      await client.query(sql);
    }
  } finally {
    client.release();
  }
}
