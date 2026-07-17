// Augment Auth.js types with our app fields (id + role) on the session/user/JWT.
import type { DefaultSession } from "next-auth";

import type { Role } from "@/lib/auth-roles";

declare module "next-auth" {
  interface User {
    role?: Role;
  }

  interface Session {
    user: {
      id: string;
      role: Role;
    } & DefaultSession["user"];
  }
}

// JWT lives in @auth/core/jwt (next-auth/jwt only re-exports it), so augment
// there for the merge to take effect.
declare module "@auth/core/jwt" {
  interface JWT {
    id?: string;
    role?: Role;
  }
}
