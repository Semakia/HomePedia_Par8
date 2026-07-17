// Seed a demo admin so the /admin area is reachable out of the box.
// Run with: npm run db:seed
// Standalone (no server-only imports) — instantiates its own Prisma client.
import bcrypt from "bcryptjs";
import { PrismaClient } from "@prisma/client";
import { PrismaBetterSqlite3 } from "@prisma/adapter-better-sqlite3";

const adapter = new PrismaBetterSqlite3({
  url: process.env.DATABASE_URL ?? "file:./prisma/dev.db",
});
const prisma = new PrismaClient({ adapter });

const ADMIN_EMAIL = "admin@homepedia.fr";
const ADMIN_PASSWORD = "admin1234";

async function main() {
  const existing = await prisma.user.findUnique({
    where: { email: ADMIN_EMAIL },
  });
  if (existing) {
    console.log(`Seed: admin already exists (${ADMIN_EMAIL}).`);
    return;
  }
  await prisma.user.create({
    data: {
      email: ADMIN_EMAIL,
      name: "Admin",
      role: "ADMIN",
      passwordHash: await bcrypt.hash(ADMIN_PASSWORD, 10),
    },
  });
  console.log(`Seed: created admin ${ADMIN_EMAIL} / ${ADMIN_PASSWORD}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(() => prisma.$disconnect());
