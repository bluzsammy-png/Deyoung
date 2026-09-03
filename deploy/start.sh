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

# ---- 2. Launch the standalone Next.js server ----
export NODE_ENV=production
export HOSTNAME=0.0.0.0
export PORT="${PORT:-3000}"
echo "[deyoung] starting server on 0.0.0.0:${PORT}"
exec node .next/standalone/server.js
