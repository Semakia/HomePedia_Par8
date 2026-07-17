# HOMEPEDIA — Next.js frontend (PROD image).
# Built from the repo root (context = repo root):
#   docker build -f iac/docker/prod/frontend/Dockerfile \
#     --build-arg NEXT_PUBLIC_API_URL=https://api.homepedia.example -t homepedia/frontend:<tag> .
#
# Base is node:22-slim (glibc), NOT alpine: the front owns its auth via Prisma 7
# + better-sqlite3 (a native module) whose prebuilt binaries and the Prisma
# engines target glibc — alpine/musl would need special handling. We run
# `next start` with full node_modules (rather than the standalone trace) so the
# native sqlite driver + generated Prisma client are guaranteed present.

# --- Stage 1: build ---------------------------------------------------------
FROM node:22-slim AS builder
WORKDIR /app

# Prisma's engine needs libssl/openssl (absent from node:22-slim).
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first. `npm ci` triggers the `postinstall` -> `prisma generate`,
# which needs the schema + prisma.config.ts present, so copy them BEFORE it.
COPY frontend/package.json frontend/package-lock.json ./
COPY frontend/prisma ./prisma
COPY frontend/prisma.config.ts ./prisma.config.ts
RUN npm ci

# Build with the public API URL inlined (NEXT_PUBLIC_* are baked at build time).
COPY frontend/ ./
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- Stage 2: runtime -------------------------------------------------------
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# Prisma query engine + `migrate deploy` at boot need openssl.
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1001 nodejs && useradd -u 1001 -g nodejs -m nextjs

# App + built assets + node_modules (Prisma client + better-sqlite3 native).
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/next.config.ts ./next.config.ts
COPY --from=builder --chown=nextjs:nodejs /app/prisma ./prisma
COPY --from=builder --chown=nextjs:nodejs /app/prisma.config.ts ./prisma.config.ts
COPY --chown=nextjs:nodejs iac/docker/prod/frontend/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# SQLite auth DB lives here on a mounted volume; pre-create it owned by nextjs so
# the volume inherits writable ownership on first mount.
RUN mkdir -p /app/data && chown nextjs:nodejs /app/data

USER nextjs
EXPOSE 3000

# Liveness: the home page renders (any <500 status is "up").
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD ["node", "-e", "require('http').get('http://127.0.0.1:3000/',r=>process.exit(r.statusCode<500?0:1)).on('error',()=>process.exit(1))"]

# Entrypoint applies pending Prisma migrations to the mounted SQLite volume,
# then starts Next.
ENTRYPOINT ["./entrypoint.sh"]
