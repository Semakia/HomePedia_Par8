// Edge/proxy-safe Auth.js config.
//
// This half intentionally imports NO Node-only code (no Prisma, no bcrypt) so it
// can be instantiated inside `proxy.ts` for route protection without dragging the
// account store into that bundle. The Credentials provider (which needs Prisma +
// bcrypt) is added in `auth.ts`, the Node-runtime half.
import type { NextAuthConfig } from "next-auth";

import { asRole } from "@/lib/auth-roles";

// Login/register: reachable while signed out, hidden once signed in.
const PUBLIC_ROUTES = ["/login", "/register"];

function isPublic(pathname: string): boolean {
  return PUBLIC_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

export const authConfig = {
  pages: { signIn: "/login" },
  session: { strategy: "jwt" },
  // Real providers are injected in auth.ts. Kept empty here so this module stays
  // free of Prisma/bcrypt for the proxy bundle.
  providers: [],
  callbacks: {
    // Runs in proxy.ts for every matched request. The app is public: only the
    // admin area requires authentication. Everything else is reachable signed
    // out (login just unlocks the account footer + the /admin section).
    authorized({ auth, request }) {
      const { pathname } = request.nextUrl;
      const isLoggedIn = !!auth?.user;

      if (isPublic(pathname)) {
        // Don't show login/register to already-authenticated users.
        if (isLoggedIn) return Response.redirect(new URL("/", request.nextUrl));
        return true;
      }

      // Admin area: signed-in ADMIN only. Anon -> /login; non-admin -> home.
      if (isAdminPath(pathname)) {
        if (!isLoggedIn) return false; // -> redirect to pages.signIn (/login)
        if (asRole(auth.user.role) !== "ADMIN") {
          return Response.redirect(new URL("/", request.nextUrl));
        }
      }

      // Every other route is public.
      return true;
    },
    // Persist id + role onto the JWT at sign-in so the session (and the proxy
    // gate above) can read them without a DB round-trip.
    jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = asRole(user.role);
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.id = token.id ?? "";
        session.user.role = asRole(token.role);
      }
      return session;
    },
  },
} satisfies NextAuthConfig;
