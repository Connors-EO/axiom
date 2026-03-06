import { Pool } from 'pg';

export const pool = new Pool({
  host: process.env.PGHOST ?? 'localhost',
  port: parseInt(process.env.PGPORT ?? '5433', 10),
  database: process.env.PGDATABASE ?? 'axiom_dev',
  user: process.env.PGUSER ?? 'axiom',
  password: process.env.PGPASSWORD ?? 'axiom',
});
