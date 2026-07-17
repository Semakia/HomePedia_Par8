// Route protection (Next 16 renamed `middleware` -> `proxy`). Instantiates a
// lean Auth.js from the edge-safe config (no Prisma) and uses its `authorized`
// callback (in auth.config.ts) to gate every matched request.
import NextAuth from "next-auth";

import { authConfig } from "@/auth.config";

// Next 16 detects the proxy handler from a default (or named `proxy`) function
// export; the destructured `export const { auth: proxy } = …` form isn't
// recognized by the build's static analysis, so we bind then default-export it.
const { auth } = NextAuth(authConfig);

export default auth;

export const config = {
  // Run on everything except Next internals, the auth API routes, and static
  // assets. The `authorized` callback decides allow/redirect per path.
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico).*)"],
};
