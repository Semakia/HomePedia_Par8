// Prisma 7 config — used by the CLI (migrate/generate). The runtime client gets
// its driver adapter in src/lib/prisma.ts. The datasource URL is read from
// DATABASE_URL so the CLI and the runtime agree on the same SQLite file — in
// prod that's the volume path (file:/app/data/prod.db); locally it falls back
// to the repo dev.db. (Not a secret.)
import { defineConfig } from "prisma/config";

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: { path: "prisma/migrations" },
  datasource: { url: process.env.DATABASE_URL ?? "file:./prisma/dev.db" },
});
