#!/bin/sh
# Frontend container entrypoint: apply pending Prisma migrations to the mounted
# SQLite account DB, then start Next. Migrations are idempotent (migrate deploy
# only applies what's missing), so this is safe on every boot.
set -e

echo "[entrypoint] applying Prisma migrations (DATABASE_URL=${DATABASE_URL})"
npx --no-install prisma migrate deploy || {
  echo "[entrypoint] migrate deploy failed" >&2
  exit 1
}

# Optional one-time seed of demo accounts when SEED_ON_START=1.
if [ "${SEED_ON_START:-0}" = "1" ]; then
  echo "[entrypoint] seeding demo accounts"
  npm run db:seed || echo "[entrypoint] seed skipped/failed (non-fatal)"
fi

echo "[entrypoint] starting Next on :${PORT:-3000}"
exec npm run start -- -p "${PORT:-3000}"
