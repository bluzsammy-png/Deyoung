import { PrismaClient } from "@prisma/client";

const SESSION_URL = "postgresql://postgres.REDACTED-C6-OLD-PROJ-REF:REDACTED-C6-DB-PASSWORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require&connection_limit=2";
const db = new PrismaClient({ datasources: { db: { url: SESSION_URL } } });

const rows = await db.$queryRawUnsafe(`
  SELECT pid, application_name, state,
         backend_start::text  AS backend_start,
         state_change::text   AS state_change,
         CASE WHEN client_addr IS NULL THEN 'internal' ELSE host(client_addr) END AS client
  FROM pg_stat_activity
  WHERE datname = current_database()
    AND application_name LIKE 'Supavisor%'
  ORDER BY backend_start
`);
console.log("Supavisor session-pooler connections (who + when):");
for (const r of rows) {
  console.log(`pid=${String(r.pid).padStart(6)}  ${r.state.padEnd(6)}  backend_start=${r.backend_start}  state_change=${r.state_change}`);
}
console.log(`\nnow = ${new Date().toISOString()}`);

await db.$disconnect();
