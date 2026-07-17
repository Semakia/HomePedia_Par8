// Prisma client singleton (Prisma 7 driver-adapter model).
//
// The account store is a local SQLite file (front-owned auth — no dependency on
// the shared Gold API/DB). A single client is cached on globalThis so Next's
// dev hot-reload doesn't open a new connection on every change.
import "server-only";

import { PrismaClient } from "@prisma/client";
import { PrismaBetterSqlite3 } from "@prisma/adapter-better-sqlite3";

const adapter = new PrismaBetterSqlite3({
  url: process.env.DATABASE_URL ?? "file:./prisma/dev.db",
});

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient({ adapter });

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}
