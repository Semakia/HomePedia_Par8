// Node-runtime Auth.js instance: full config = edge-safe base (auth.config.ts)
// plus the Credentials provider, which needs Prisma + bcrypt. Used by the route
// handler (api/auth/[...nextauth]) and Server Actions/Components.
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";

import { authConfig } from "@/auth.config";
import { asRole } from "@/lib/auth-roles";
import { prisma } from "@/lib/prisma";

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Mot de passe", type: "password" },
      },
      async authorize(credentials) {
        const email = String(credentials?.email ?? "")
          .trim()
          .toLowerCase();
        const password = String(credentials?.password ?? "");
        if (!email || !password) return null;

        const user = await prisma.user.findUnique({ where: { email } });
        // Compare even when the user is unknown? Not worth the ceremony here;
        // return null uniformly so we never leak which of email/password failed.
        if (!user) return null;

        const ok = await bcrypt.compare(password, user.passwordHash);
        if (!ok) return null;

        return {
          id: user.id,
          email: user.email,
          name: user.name,
          role: asRole(user.role),
        };
      },
    }),
  ],
});
