// Auth.js REST endpoints (sign-in/out, session, callbacks). Runs on Node so the
// Credentials authorize() can reach Prisma + bcrypt.
import { handlers } from "@/auth";

export const { GET, POST } = handlers;
