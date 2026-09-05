#!/bin/sh
# DeYoung — Railway/Railpack production start.
# Build step (Railway custom build command) has already produced .next/standalone
# and generated the Prisma client from prisma/schema.postgres.prisma.
set -u

echo "[deyoung] boot — node $(node -v)"

# ---- 1. Sync database schema (idempotent, non-fatal) ----
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[deyoung] WARNING: DATABASE_URL is not set — admin/content APIs will fail until it is added."
else
  if [ -x ./node_modules/.bin/prisma ]; then
    echo "[deyoung] syncing database schema (prisma db push)…"
    ./node_modules/.bin/prisma db push \
      --schema prisma/schema.postgres.prisma \
      --skip-generate --accept-data-loss \
      || echo "[deyoung] WARNING: db push failed (continuing — tables may already exist)"
    echo "[deyoung] seeding demo content if empty…"
    node scripts/seed.ts || echo "[deyoung] WARNING: seed skipped (may already be seeded)"
  else
    echo "[deyoung] NOTE: prisma CLI not present at runtime — assuming database is already provisioned."
  fi
fi

# ---- 2. App runtime: switch to Supabase transaction-mode pooler (:6543) ----
# The session-mode pooler (:5432) pins one server connection per client and is
# capped at pool_size 15. During a Railway deploy the old release keeps serving
# while the new one boots, so both Prisma pools together exceed 15 clients and
# every query fails with `EMAXCONNSESSION max clients reached in session mode`
# — which fails the /api/home healthcheck. Transaction mode (:6543) multiplexes
# many clients over few server connections and is safe under deploy overlap.
# Schema operations above (db push / seed) intentionally still used :5432.
if [ -n "${DATABASE_URL:-}" ]; then
  case "$DATABASE_URL" in
    *pooler.supabase.com:5432*)
      APP_DB_URL="$(printf '%s' "$DATABASE_URL" | sed 's/pooler\.supabase\.com:5432/pooler.supabase.com:6543/')"
      case "$APP_DB_URL" in
        *\?*) APP_DB_URL="${APP_DB_URL}&pgbouncer=true&connection_limit=5&pool_timeout=20" ;;
        *)    APP_DB_URL="${APP_DB_URL}?pgbouncer=true&connection_limit=5&pool_timeout=20" ;;
      esac
      export DATABASE_URL="$APP_DB_URL"
      echo "[deyoung] app runtime → transaction-mode pooler :6543 (pgbouncer=true, connection_limit=5)"
      ;;
    *)
      echo "[deyoung] DATABASE_URL is not the Supabase session pooler — using it as-is"
      ;;
  esac
fi

# ---- 3. Launch the standalone Next.js server ----
export NODE_ENV=production
export HOSTNAME=0.0.0.0
export PORT="${PORT:-3000}"
echo "[deyoung] starting server on 0.0.0.0:${PORT}"
exec node .next/standalone/server.js
