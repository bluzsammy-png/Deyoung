-- DeYoung worker-plane direct-DB access (one-off setup).
-- Creates a least-privilege role for the Kaggle GPU fleet so workers never
-- depend on the site's HTTP API (Railway's edge rate-limits datacenter IPs).
-- Run: DATABASE_URL=... psql "$DATABASE_URL" -f scripts/worker_db_setup.sql
-- (password is generated here and echoed once — bake it into private kernels)

DO $$
DECLARE
  pw text := 'dywdb_' || encode(gen_random_bytes(20), 'hex');
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'worker_bot') THEN
    EXECUTE format('CREATE ROLE worker_bot LOGIN PASSWORD %L', pw);
  ELSE
    EXECUTE format('ALTER ROLE worker_bot LOGIN PASSWORD %L', pw);
  END IF;
  RAISE NOTICE 'WORKER_DB_PASSWORD=%', pw;
END $$;

-- artifact store for fleet deliveries (scene mp4s land here as bytes)
CREATE TABLE IF NOT EXISTS "WorkerArtifact" (
  id          text PRIMARY KEY,
  "requestId" text NOT NULL,
  mime        text NOT NULL DEFAULT 'video/mp4',
  bytes       bytea NOT NULL,
  size        integer NOT NULL DEFAULT 0,
  "createdAt" timestamptz NOT NULL DEFAULT now()
);

GRANT USAGE ON SCHEMA public TO worker_bot;
GRANT SELECT, UPDATE ON "VideoRequest" TO worker_bot;
GRANT INSERT ON "WorkerArtifact" TO worker_bot;
GRANT SELECT ON "WorkerArtifact" TO worker_bot;

-- keep the role boxed in
REVOKE CREATE ON SCHEMA public FROM worker_bot;
REVOKE ALL ON DATABASE postgres FROM worker_bot;
GRANT CONNECT ON DATABASE postgres TO worker_bot;
